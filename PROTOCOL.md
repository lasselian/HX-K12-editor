# HX-K12 / Romoral macro pad — USB protocol

Reverse-engineered from the OEM **MINI KeyBoard** Windows app (.NET) and then
**verified byte-for-byte on real hardware** (USB `1189:8840`) by programming keys
and reading back what they emit on the keyboard interface.

## Device / transport

- VID:PID = `1189:8840` (the `1189` "Acer" VID is reused by many OEM pads).
- Two HID interfaces:
  - `mi_00` — vendor-defined (Usage Page `0xFF00`) → **config channel**
    (`/dev/hidrawN`, the one whose report descriptor starts `06 00 FF`).
  - `mi_01` — keyboard + mouse + consumer. This is what the OS sees, and what
    we read from to verify programming. Report IDs: `1`/`4` keyboard,
    `2` mouse, `5` consumer (16-bit usage).
- Writes go to the vendor interface as a 65-byte buffer (report-ID byte + 64).

## Program-a-key report (65 bytes) — VERIFIED

| Offset | Meaning |
|-------:|---------|
| 0  | `0xFE` — report-ID byte / command |
| 1  | `0xFE` — command marker |
| 2  | key number (physical key 1..12, or knob slot 16..21) |
| 3  | layer (1-based) |
| 4  | key type: `0x01` keyboard, `0x02` media/consumer |
| 5–9 | 0 |
| 10 | keystroke **count** (keyboard only) |
| 11 | keystroke-1 **modifier**  •or•  consumer-usage **low** byte (media) |
| 12 | keystroke-1 **keycode**   •or•  consumer-usage **high** byte (media) |
| 13,14 | keystroke-2 modifier, keycode … (macros continue in pairs) |
| … | padding to 65 |

The double `0xFE` is real: the OEM's `HidLib.WriteDevice` sets the HID report-ID
to `arrayBuff[0]` (`0xFE`) **and** keeps `0xFE` as the first data byte, so the
on-wire buffer begins `FE FE …`. Writing a single `FE` does not program the key.

## Flash-commit report (65 bytes)

`[0x00, 0xAA, 0xAA, 0x00 …]` — persists the just-written key(s) to flash. (The
OEM builds this via `Send_WriteFlash_Cmd` with report-ID 0.) Write the key
report(s), then one commit.

## Key types & values

- **Keyboard** (`type 0x01`): standard USB HID keyboard **usage IDs**
  (`A`=0x04 … `L`=0x0F, `F1`=0x3A …). Modifier byte uses standard HID bits
  (LCtrl 0x01, LShift 0x02, LAlt 0x04, LGui 0x08; right-hand variants `<<4`).
  `count` = number of (modifier,keycode) pairs → enables **multi-key macros**.
- **Media** (`type 0x02`): a real 16-bit HID **Consumer-page usage**, written
  low byte at offset 11, high at 12. The firmware emits this value verbatim, so
  it must be the real code — **not** the OEM's internal numbers. Verified:
  Mute `0xE2`, Vol+ `0xE9`, Vol- `0xEA`, Play/Pause `0xCD`, Next `0xB5`,
  Prev `0xB6`, Stop `0xB7`.
  (The OEM app stores small internal values like `0x04` for mute; the device
  echoes whatever it's given, so those produce the bogus consumer usage `0x0004`
  — which is exactly why our first attempts "did nothing".)

## Slots (this 12-key + 2-knob unit, `New_Mul_Mouse=1`)

- Keys: physical key *n* → slot *n* (1..12). Factory default: key *n* types the
  *n*-th letter (key1=A, key2=B, …).
- Knobs: K1 = 16/17/18, K2 = 19/20/21 (turn-left / press / turn-right).

## Worked examples (verified)

```
Key 1 = Mute      : FE FE 01 01 02 00 00 00 00 00 00 E2 00 …   then 00 AA AA …
Key 5 = "a"       : FE FE 05 01 01 00 00 00 00 00 01 00 04 00 …
Key 6 = Ctrl+C    : FE FE 06 01 01 00 00 00 00 00 01 01 06 00 …
```

## Notes

- Single-key program+commit works (no need to rewrite the whole layout); each
  key persists independently.
- Wine can *read* the device but its HID **write** fails before reaching USB, so
  the OEM app can't program under Wine — irrelevant now that this is implemented
  natively.
- LED modes/colors and mouse actions exist in the OEM app and are not yet
  implemented here (see README roadmap).
