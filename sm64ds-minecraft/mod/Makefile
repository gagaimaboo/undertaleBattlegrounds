PREFIX  ?= arm-none-eabi-
FLAGS   := -mcpu=arm946e-s -marm -Os -ffreestanding -nostdlib -fno-builtin -ffunction-sections
CXXFLAGS:= $(FLAGS) -std=c++17 -fno-exceptions -fno-rtti -fno-threadsafe-statics -Wall -Wextra
OBJS    := build/hooks.o build/main.o

all: build/mod.bin

build/%.o: source/%.cpp | build ; $(PREFIX)g++ $(CXXFLAGS) -c $< -o $@
build/%.o: source/%.s   | build ; $(PREFIX)as -mcpu=arm946e-s $< -o $@
build/mod.elf: $(OBJS) linker.ld ; $(PREFIX)ld -T linker.ld --gc-sections $(OBJS) -o $@ -Map build/mod.map
build/mod.bin: build/mod.elf ; $(PREFIX)objcopy -O binary $< $@
build: ; mkdir -p build
clean: ; rm -rf build
.PHONY: all clean
