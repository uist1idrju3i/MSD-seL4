// SPDX-License-Identifier: BSD-3-Clause
// QEMU-only experiment: Rust port of projects/smoke/main.c using rust-sel4 v6.0.0.
#![no_std]
#![no_main]

use sel4::CapTypeForObjectOfFixedSize;
use sel4::init_thread::{Slot, slot};
use sel4_root_task::root_task;

const PL011_PADDR: usize = 0x3f20_1000;
const UART_VADDR: usize = 0x8000_0000;
const PAGE_BITS: usize = 12;

struct Slots(core::ops::Range<usize>);

impl Slots {
    fn take(&mut self, n: usize) -> usize {
        let i = self.0.start;
        assert!(i + n <= self.0.end);
        self.0.start += n;
        i
    }
}

fn uart_putc(c: u8) {
    let base = UART_VADDR as *mut u32;
    unsafe {
        while core::ptr::read_volatile(base.add(0x18 / 4)) & (1 << 5) != 0 {}
        core::ptr::write_volatile(base, c as u32);
    }
}

fn uart_puts(s: &str) {
    for b in s.bytes() {
        if b == b'\n' {
            uart_putc(b'\r');
        }
        uart_putc(b);
    }
}

#[root_task(heap_size = 4096)]
fn main(bootinfo: &sel4::BootInfoPtr) -> ! {
    let cnode = slot::CNODE.cap().absolute_cptr_for_self();
    let mut slots = Slots(bootinfo.empty().range());

    let (dev_ix, dev) = bootinfo
        .untyped_list()
        .iter()
        .enumerate()
        .find(|(_, d)| {
            d.is_device() && (d.paddr()..d.paddr() + (1 << d.size_bits())).contains(&PL011_PADDR)
        })
        .unwrap();
    let mut cur = bootinfo.untyped().index(dev_ix).cap();
    let mut base = dev.paddr();
    let mut bits = dev.size_bits();
    // Split by halves; deleting a lone child would reset the untyped watermark.
    while bits > PAGE_BITS {
        bits -= 1;
        let halves = slots.take(2);
        cur.untyped_retype(&sel4::ObjectBlueprint::Untyped { size_bits: bits }, &cnode, halves, 2)
            .unwrap();
        let upper = PL011_PADDR - base >= 1 << bits;
        if upper {
            base += 1 << bits;
        }
        cur = Slot::<sel4::cap_type::Untyped>::from_index(halves + upper as usize).cap();
    }
    let frame_ix = slots.take(1);
    cur.untyped_retype(&sel4::cap_type::Granule::object_blueprint(), &cnode, frame_ix, 1)
        .unwrap();

    let (ram_ix, _) = bootinfo
        .untyped_list()
        .iter()
        .enumerate()
        .filter(|(_, d)| !d.is_device())
        .max_by_key(|(_, d)| d.size_bits())
        .unwrap();
    let pt_ix = slots.take(1);
    bootinfo
        .untyped()
        .index(ram_ix)
        .cap()
        .untyped_retype(&sel4::cap_type::PT::object_blueprint(), &cnode, pt_ix, 1)
        .unwrap();
    Slot::<sel4::cap_type::PT>::from_index(pt_ix)
        .cap()
        .pt_map(slot::VSPACE.cap(), UART_VADDR, sel4::VmAttributes::DEFAULT)
        .unwrap();
    // No PAGE_CACHEABLE: AArch32 seL4 maps the frame strongly ordered.
    Slot::<sel4::cap_type::Granule>::from_index(frame_ix)
        .cap()
        .frame_map(
            slot::VSPACE.cap(),
            UART_VADDR,
            sel4::CapRights::read_write(),
            sel4::VmAttributes::EXECUTE_NEVER,
        )
        .unwrap();

    uart_puts("MSD-seL4 rust smoke: root task started\nMSD-seL4 rust smoke: OK\n");
    sel4::init_thread::suspend_self()
}
