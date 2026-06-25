# HX-K12 Editor

<img width="802" height="700" alt="image" src="https://github.com/user-attachments/assets/2dfb4d24-fb9b-41a2-8241-00437cffa889" />


A free, cross-platform app for programming the HX-K12 / Romoral macro pad (the
little USB keypad with `1189:8840` on it). It replaces the clunky Windows-only
"MINI KeyBoard" software that comes with the pad.

Whatever you set up here gets written into the keyboard's own memory, so your
keys and knobs keep working on any computer afterwards, with nothing running in
the background. Program it once, unplug it, plug it into anything.

It comes with a clean graphical editor and a command line, and it works on
Linux, Windows, and macOS. The way the keyboard is programmed was figured out by
studying the original app. The details are in [PROTOCOL.md](PROTOCOL.md).

This is a working version 1 and has been tested on a real pad: keys and knobs
were reprogrammed to media controls and macros and read back to confirm it
stuck.

## What you get

- A visual editor showing your 12 keys and 2 knobs. Click anything to change it.
- Three layers, so each key can do three different things.
- Media keys (mute, volume, play, next, previous), single keys, key combos like
  `Ctrl+C`, and full multi key macros.
- A record button: instead of typing a macro, press the keys and it captures
  them in order.
- Save and load your setups as files, so you can keep several and switch between
  them.
- Reopens with your last layout, so you do not start from a blank grid every
  time.
- Follows your system light or dark theme.

## Quick start (Linux)

This is the easy path. You need Python 3 (Fedora, Ubuntu and most Linux systems
already have it).

1. Get the code. Download this repository (or clone it with `git`), then open a
   terminal in the folder you ended up with:

   ```bash
   cd HX-K12-editor
   ```

2. Run the launcher:

   ```bash
   ./run.sh
   ```

That is it. The first time, `run.sh` sets up everything it needs in a private
folder, asks once for your password to allow the keyboard to be reprogrammed,
and opens the editor. Every time after that it just opens the editor.

If a key or knob is not detected the first time, unplug the pad and plug it back
in, then start `run.sh` again.

> Tip: many file managers let you mark `run.sh` as runnable (Properties, then
> "allow executing as a program") and start it with a double click. Running it
> from a terminal is the most reliable, though, because you can see any messages.

## Quick start (Windows and macOS)

`run.sh` is for Linux and macOS terminals. On Windows, or if you would rather do
the steps yourself, see "Doing it by hand" below.

## Using the editor

When the window opens you see your keys laid out as a grid, with the two knobs
below them.

- Click any key to choose what it does. You can pick a media key, a single key,
  a key combo, or a multi key macro.
- For a macro, either type the combo (for example `ctrl+c`) or click the record
  button and just press the keys you want. Each keystroke is captured in the
  order you press them.
- Each knob has three actions you can set separately: turn left, press, and turn
  right.
- Use the Layer selector at the top to switch between the three layers.
- When you are happy, click "Flash to keyboard". This writes the current layer
  into the pad's memory.
- The menu has New, Open, and Save so you can keep your setups as files and load
  them again later.

Nothing is written to the keyboard until you click "Flash to keyboard", so you
can experiment freely.

The editor remembers what you set and reopens with it next time, so you are not
looking at a blank grid on every launch. One thing to know: this is the layout
you built here, kept on your computer. The pad has no way to report back what is
currently stored on it, so the editor cannot read a setup that was put there by
the original Windows app or on another machine. Use Save and Open if you want to
keep several named layouts.

## Command line

If you prefer the terminal, or want to script things, there is a command line
too. With the launcher you can reach it like this:

```bash
# check the pad is connected
./run.sh cli info

# see exactly what would be sent, without writing anything
./run.sh cli set-key 1 mute --dry-run

# set physical key 1 to Mute and save it to the pad
./run.sh cli set-key 1 mute

# set key 5 to Ctrl+C
./run.sh cli set-key 5 "ctrl+c"
```

If you installed by hand (below), replace `./run.sh cli` with `python -m hxk12`.

Actions you can use: `mute`, `vol+`, `vol-`, `play`, `prev`, `next`, single keys
like `f13`, `a`, or `enter`, and combos like `ctrl+shift+p`. The full list lives
in `hxk12/keycodes.py`.

## Doing it by hand

You do not need this if `run.sh` works for you. These are the same steps the
launcher does, in case you are on Windows or want more control.

**1. Allow the keyboard to be reprogrammed (Linux only).** This grants access to
the pad and only has to be done once:

```bash
sudo install -m644 udev/99-hx-k12.rules /etc/udev/rules.d/99-hx-k12.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Then unplug the pad and plug it back in.

**2. Install the editor.**

```bash
# Linux
pip install -e ".[gui]"

# Windows and macOS (these also need the hidapi backend)
pip install -e ".[gui,hid]"
```

**3. Run it.**

```bash
# graphical editor
python -m hxk12 gui

# or the command line
python -m hxk12 info
```

## Troubleshooting

**The editor says it cannot find the pad.** Make sure it is plugged in. On Linux,
unplug and replug after installing the permission rule, so the new permission
takes effect.

**It found the pad but cannot write to it (a permission error).** On Linux the
permission rule is missing or did not apply yet. Run step 1 under "Doing it by
hand", then unplug and replug. On macOS, grant input monitoring permission to
your terminal or to Python in System Settings.

**Python is not found.** Install Python 3.9 or newer, then try again. On Linux it
is usually already there as `python3`.

## How it works

The pad shows up as a normal USB HID device. The editor talks to its vendor
configuration interface to write key and knob assignments straight into flash,
the same way the original Windows app does. On Linux this uses the built in
hidraw interface with no extra libraries. On Windows and macOS it uses hidapi.
The full protocol, including the byte formats, is written up in
[PROTOCOL.md](PROTOCOL.md).

## Roadmap

- [x] Decompile the original app and document the protocol
- [x] Byte accurate encoder for keyboard and media actions, with a dry run mode
- [x] Cross-platform device layer (hidraw and hidapi)
- [x] Graphical editor: visual key and knob editing, layers, multi key macros,
      saved profiles
- [x] Verified on real hardware (keys and knobs reprogrammed and read back)
- [ ] LED modes and colors, mouse actions, per key delay
- [ ] Read back and backup of the current config (if the pad supports it)
- [ ] Standalone installers so Python is not needed

## License

MIT.
