/* custom code lives in free RAM right after the highest overlay (EUR: ov102 ends 0x0214EAA0).
   tools/patch_rom.py bumps the game's main-arena start past __mod_end so the heap never touches it. */
OUTPUT_ARCH(arm)
ENTRY(mod_hook_player_behavior)
SECTIONS
{
    . = 0x0214EAA0;
    .text : {
        __mod_start = .;
        *(.text.hooks)
        *(.text .text.*)
        *(.rodata .rodata.*)
        *(.data .data.*)
        . = ALIGN(4);
        __bss_start = .;
        *(.bss .bss.* COMMON)
        . = ALIGN(32);
        __mod_end = .;
    }
    /DISCARD/ : { *(.ARM.exidx*) *(.ARM.attributes) *(.comment) *(.note*) }
}
