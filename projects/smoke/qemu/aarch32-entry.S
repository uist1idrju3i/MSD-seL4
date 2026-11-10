/* SPDX-License-Identifier: BSD-3-Clause */
/*
 * QEMU raspi3b starts a -kernel ELF in AArch64. The verified seL4
 * configuration is AArch32, so this stub switches the lower exception levels
 * to AArch32 and jumps to the elfloader entry. From EL3 it enters AArch32 HYP
 * mode, like the real firmware with arm_64bit=0; from EL2 it can only enter
 * AArch32 SVC mode. This stub exists only for the QEMU smoke test.
 */
    .section .text.entry, "ax"
    .global _start
_start:
    /* Only core 0 boots; the kernel is configured for a single node. */
    mrs     x11, mpidr_el1
    and     x11, x11, #0xff
    cbnz    x11, park
    ldr     x10, =ELFLOADER_ENTRY
    mov     x0, #0
    mov     x1, #0
    mov     x2, #0
    /* Let EL1 use the physical counter and timer. */
    mov     x9, #3
    mrs     x11, CurrentEL
    cmp     x11, #(3 << 2)
    b.eq    from_el3
    cmp     x11, #(2 << 2)
    b.eq    from_el2
park:
    wfe
    b       park

from_el3:
    msr     cnthctl_el2, x9
    msr     cntvoff_el2, xzr
    /* SCR_EL3: NS = 1, HCE = 1, RW = 0 (EL2 and EL1 run AArch32). */
    mov     x9, #((1 << 0) | (1 << 8))
    msr     scr_el3, x9
    /* AArch32 HYP mode with A, I and F masked. */
    mov     x9, #0x1da
    msr     spsr_el3, x9
    msr     elr_el3, x10
    isb
    eret

from_el2:
    msr     cnthctl_el2, x9
    msr     cntvoff_el2, xzr
    /* HCR_EL2.RW = 0: EL1 runs AArch32. */
    msr     hcr_el2, xzr
    /* AArch32 SVC mode with A, I and F masked. */
    mov     x9, #0x1d3
    msr     spsr_el2, x9
    msr     elr_el2, x10
    isb
    eret
