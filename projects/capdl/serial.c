/* SPDX-License-Identifier: BSD-3-Clause */
#include "protocol.h"
#include "serial-config.h"

static int putc_uart(char c)
{
    volatile seL4_Word *uart = (volatile seL4_Word *)MSD_VADDR_UART;
    unsigned int limit = 1000000;
    while (uart[0x18 / 4] & (1u << 5)) {
        if (--limit == 0) {
            return 0;
        }
    }
    uart[0] = (unsigned char)c;
    return 1;
}

static void puts_uart(const char *s)
{
    for (; *s; s++) {
        if ((*s == '\n' && !putc_uart('\r')) || !putc_uart(*s)) {
            idle();
        }
    }
}

void __sel4_start_c(const void *stack);
void __sel4_start_c(const void *stack)
{
    (void)stack;
    component_init(MSD_IPC_BUFFER);
    unsigned int stage = 0;
    seL4_Word mode = 0;
    for (;;) {
        seL4_Word badge = 0;
        seL4_MessageInfo_t info = seL4_Recv(MSD_CAP_RECEIVE, &badge);
        seL4_Word label = seL4_MessageInfo_get_label(info);
        seL4_Word length = seL4_MessageInfo_get_length(info);
        if (badge == 2 && stage == 2 && mode == 1 && label == seL4_Fault_VMFault &&
            length == seL4_VMFault_Length && seL4_GetMR(seL4_VMFault_Addr) == PL011_PADDR &&
            seL4_GetMR(seL4_VMFault_PrefetchFault) == 0) {
            puts_uart("MSD-seL4 capdl: client faulted at 0x3f201000\n");
            /* Do not reply: the faulted client remains blocked. */
            continue;
        }
        if (badge == 1 && label == 0 && length == 2 && seL4_GetMR(1) <= 1) {
            if (stage == 0 && seL4_GetMR(0) == REQUEST) {
                mode = seL4_GetMR(1);
                stage = 1;
                puts_uart("MSD-seL4 capdl: serial got badge 1 from client\n");
            } else if (stage == 1 && seL4_GetMR(0) == ACK && seL4_GetMR(1) == mode) {
                stage = 2;
                puts_uart("MSD-seL4 capdl: client checked reply\n");
            } else {
                puts_uart("MSD-seL4 capdl: ERROR unexpected request\n");
                continue;
            }
            seL4_SetMR(0, REPLY);
            seL4_Reply(seL4_MessageInfo_new(0, 0, 0, 1));
        } else {
            puts_uart("MSD-seL4 capdl: ERROR unexpected badge or fault\n");
        }
    }
}
