// steve mod — phase 1 "hello world": prove our code runs inside the player's update loop.
// hold L -> the player floats upward (same speed the old EUR hover template used).
#include <stdint.h>

namespace {
constexpr uintptr_t KEYINPUT = 0x04000130;   // DS hardware, active-low (0 = pressed)
constexpr uint16_t  KEY_L    = 1 << 9;

constexpr uint32_t ACTOR_VERT_ACCEL = 0x9C;  // Actor::vertAccel (Fix12i): gravity, added to speed.y after us
constexpr uint32_t ACTOR_SPEED_Y   = 0xA8;   // Actor::speed.y (Fix12i), see SM64DS-PI Actor.h
constexpr int32_t  FLOAT_UP_SPEED  = 0x3B23; // ~3.7 units/frame in 20.12 fixed point

inline uint16_t keysHeld() { return ~*reinterpret_cast<volatile uint16_t*>(KEYINPUT) & 0x3FF; }
template <typename T> inline T& field(void* obj, uint32_t off) {
    return *reinterpret_cast<T*>(static_cast<uint8_t*>(obj) + off);
}
}

// debug breadcrumbs, readable from RAM by the test harness (addresses in build/mod.map)
extern "C" {
volatile uint32_t mod_debug_frames;   // increments every Player::Behavior call
void* volatile    mod_debug_player;   // last Player* seen
}

extern "C" void onPlayerBehavior(void* player)
{
    mod_debug_frames = mod_debug_frames + 1;
    mod_debug_player = player;
}

// gravity (vertAccel, which changes with the player's state: measured -2.7 / -3.6 / -8.0) is added
// to speed.y after this runs, so pre-subtract it: the speed that survives the frame is FLOAT_UP_SPEED.
extern "C" void onPlayerBehaviorLate(void* player)
{
    if (keysHeld() & KEY_L)
        field<int32_t>(player, ACTOR_SPEED_Y) = FLOAT_UP_SPEED - field<int32_t>(player, ACTOR_VERT_ACCEL);
}
