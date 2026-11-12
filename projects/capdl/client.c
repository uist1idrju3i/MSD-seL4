/* SPDX-License-Identifier: BSD-3-Clause */
#include "protocol.h"
#include "client-config.h"

static int call(seL4_Word operation)
{
    seL4_SetMR(0, operation);
    seL4_SetMR(1, CAPDL_TEST_MODE);
    seL4_MessageInfo_t reply = seL4_Call(MSD_CAP_SEND, seL4_MessageInfo_new(0, 0, 0, 2));
    return seL4_MessageInfo_get_label(reply) == 0 &&
           seL4_MessageInfo_get_length(reply) == 1 && seL4_GetMR(0) == REPLY;
}

void __sel4_start_c(const void *stack);
void __sel4_start_c(const void *stack)
{
    (void)stack;
    component_init(MSD_IPC_BUFFER);
    if (CAPDL_TEST_MODE == 2) {
        idle();
    }
    if (!call(REQUEST) || !call(ACK)) {
        idle();
    }
    if (CAPDL_TEST_MODE == 1) {
        seL4_Word value = *(volatile seL4_Word *)PL011_PADDR;
        (void)value;
        (void)call(ACCESS_RETURNED);
    }
    idle();
}
