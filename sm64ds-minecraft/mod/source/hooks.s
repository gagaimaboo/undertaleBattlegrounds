@ trampolines from patched game instructions into our C++.
@ tools/patch_rom.py overwrites each hooked instruction with "b <trampoline>" (see HOOKS there).
    .syntax unified
    .arm
    .section .text.hooks, "ax"

@ Player::Behavior entry (EUR ov2 0x020E4D24) — overwritten instr: push {r4, r5, r6, lr}
    .global mod_hook_player_behavior
mod_hook_player_behavior:
    push    {r0-r3, r12, lr}        @ 6 regs = 24 bytes, keeps sp 8-aligned
    bl      onPlayerBehavior        @ r0 = Player* (this)
    pop     {r0-r3, r12, lr}
    push    {r4, r5, r6, lr}        @ replay the overwritten instruction
    ldr     pc, =0x020E4D28

@ inside Player::Behavior (EUR ov2 0x020E50AC), same spot the old EUR hover template used.
@ mid-function: every register is live, and r5 holds this. overwritten instr: mul r0, r4, r0
    .global mod_hook_player_behavior_late
mod_hook_player_behavior_late:
    push    {r0-r12, lr}            @ 14 regs = 56 bytes, keeps sp 8-aligned
    mov     r0, r5
    bl      onPlayerBehaviorLate
    pop     {r0-r12, lr}
    mul     r0, r4, r0              @ replay the overwritten instruction (flags untouched)
    ldr     pc, =0x020E50B0
    .pool
