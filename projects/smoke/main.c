/* SPDX-License-Identifier: BSD-3-Clause */
/*
 * Minimal root task: map the PL011 UART from a device untyped, print a
 * message and the boot information summary, then suspend itself.
 * The kernel is built without printing, so this task owns the UART.
 */
#include <sel4/sel4.h>
#include <sel4runtime.h>

#define PL011_PADDR 0x3f201000u
#define PL011_DR 0x00u
#define PL011_FR 0x18u
#define PL011_FR_TXFF (1u << 5)
#define UART_VADDR 0x80000000u

static volatile seL4_Uint32 *uart;

/* sel4runtime needs memset; this task links no C library. */
void *memset(void *dest, int c, unsigned int n);
void *memset(void *dest, int c, unsigned int n)
{
    unsigned char *p = dest;
    while (n-- > 0) {
        *p++ = (unsigned char)c;
    }
    return dest;
}

static void uart_putc(char c)
{
    while (uart[PL011_FR / 4] & PL011_FR_TXFF) {
    }
    uart[PL011_DR / 4] = (seL4_Uint32)(unsigned char)c;
}

static void uart_puts(const char *s)
{
    for (; *s != '\0'; s++) {
        if (*s == '\n') {
            uart_putc('\r');
        }
        uart_putc(*s);
    }
}

static void uart_puthex(seL4_Word value)
{
    uart_puts("0x");
    for (int shift = (int)(sizeof(value) * 8) - 4; shift >= 0; shift -= 4) {
        uart_putc("0123456789abcdef"[(value >> shift) & 0xfu]);
    }
}

static seL4_CPtr next_slot;
static seL4_CPtr last_slot;

static seL4_CPtr alloc_slot(void)
{
    if (next_slot >= last_slot) {
        return seL4_CapNull;
    }
    return next_slot++;
}

/* Retype one object of the given type from untyped into a fresh slot. */
static seL4_CPtr retype(seL4_CPtr untyped, seL4_Word type, seL4_Word size_bits)
{
    seL4_CPtr slot = alloc_slot();
    if (slot == seL4_CapNull) {
        return seL4_CapNull;
    }
    seL4_Error err = seL4_Untyped_Retype(untyped, type, size_bits, seL4_CapInitThreadCNode,
                                         0, 0, slot, 1);
    return err == seL4_NoError ? slot : seL4_CapNull;
}

static seL4_CPtr find_untyped(const seL4_BootInfo *bi, seL4_Word paddr, int device,
                              seL4_Word min_bits)
{
    for (seL4_CPtr cap = bi->untyped.start; cap < bi->untyped.end; cap++) {
        const seL4_UntypedDesc *desc = &bi->untypedList[cap - bi->untyped.start];
        if ((int)desc->isDevice != device || desc->sizeBits < min_bits) {
            continue;
        }
        seL4_Word size = (seL4_Word)1 << desc->sizeBits;
        if (!device || (paddr >= desc->paddr && paddr - desc->paddr < size)) {
            return cap;
        }
    }
    return seL4_CapNull;
}

/*
 * Split the device untyped in halves until a 4 KiB untyped covers paddr,
 * then retype that into a frame. Deleting a lone child would reset the
 * untyped watermark, so walking by repeated retype is not used.
 */
static seL4_CPtr device_frame(const seL4_BootInfo *bi, seL4_Word paddr)
{
    seL4_CPtr cur = find_untyped(bi, paddr, 1, seL4_PageBits);
    if (cur == seL4_CapNull) {
        return seL4_CapNull;
    }
    const seL4_UntypedDesc *desc = &bi->untypedList[cur - bi->untyped.start];
    seL4_Word base = desc->paddr;
    seL4_Word bits = desc->sizeBits;
    while (bits > seL4_PageBits) {
        if (next_slot + 2 > last_slot) {
            return seL4_CapNull;
        }
        seL4_CPtr halves = next_slot;
        bits--;
        if (seL4_Untyped_Retype(cur, seL4_UntypedObject, bits, seL4_CapInitThreadCNode,
                                0, 0, halves, 2) != seL4_NoError) {
            return seL4_CapNull;
        }
        next_slot += 2;
        seL4_Word half = (seL4_Word)1 << bits;
        if (paddr - base >= half) {
            cur = halves + 1;
            base += half;
        } else {
            cur = halves;
        }
    }
    return retype(cur, seL4_ARM_SmallPageObject, 0);
}

int main(void)
{
    const seL4_BootInfo *bi = sel4runtime_bootinfo();
    if (bi == 0) {
        return 1;
    }
    next_slot = bi->empty.start;
    last_slot = bi->empty.end;

    seL4_CPtr frame = device_frame(bi, PL011_PADDR);
    seL4_CPtr ram = find_untyped(bi, 0, 0, seL4_PageTableBits);
    if (frame == seL4_CapNull || ram == seL4_CapNull) {
        return 2;
    }
    seL4_CPtr pt = retype(ram, seL4_ARM_PageTableObject, 0);
    if (pt == seL4_CapNull) {
        return 3;
    }
    if (seL4_ARM_PageTable_Map(pt, seL4_CapInitThreadVSpace, UART_VADDR,
                               seL4_ARM_Default_VMAttributes) != seL4_NoError) {
        return 4;
    }
    /*
     * Without seL4_ARM_PageCacheable the AArch32 kernel maps the frame as
     * strongly-ordered memory, which suits MMIO; ExecuteNever sets XN.
     */
    if (seL4_ARM_Page_Map(frame, seL4_CapInitThreadVSpace, UART_VADDR, seL4_ReadWrite,
                          seL4_ARM_ExecuteNever) != seL4_NoError) {
        return 5;
    }
    uart = (volatile seL4_Uint32 *)UART_VADDR;

    uart_puts("MSD-seL4 smoke: root task started\n");
    uart_puts("untyped caps: ");
    uart_puthex(bi->untyped.end - bi->untyped.start);
    uart_puts("\nempty slots: ");
    uart_puthex(bi->empty.end - bi->empty.start);
    uart_puts("\nMSD-seL4 smoke: OK\n");

    seL4_TCB_Suspend(seL4_CapInitThreadTCB);
    return 0;
}
