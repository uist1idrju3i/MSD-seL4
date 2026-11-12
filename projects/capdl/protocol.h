/* SPDX-License-Identifier: BSD-3-Clause */
#pragma once
#include <sel4/sel4.h>
#include <sel4runtime.h>

#define REQUEST 0xc0ffee01u
#define ACK 0xacce5501u
#define ACCESS_RETURNED 0xbad00001u
#define REPLY 0x600d0001u
#define PL011_PADDR 0x3f201000u

static inline void component_init(seL4_Word ipc)
{
    /* CapDL supplies SP and zeroed RAM, not a System V stack or auxv. No TLS. */
    sel4runtime_set_tls_base(0);
    seL4_SetIPCBuffer((seL4_IPCBuffer *)ipc);
}

static inline void idle(void)
{
    for (;;) {
        seL4_Yield();
    }
}
