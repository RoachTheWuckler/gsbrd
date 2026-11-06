**GSBRD**

gsbrd is a highly customizable, cross-platform input overlay for streaming in recording, written in python.


*This is a personal project so don't expect much from it. Basically a worse version of `Input Overlay` for OBS*

Configuration uses the JSON file format. There are a few examples in the `presets/` directory. I will make proper docs for that later.

**Install**
Ensure you have Python 3.14+ and `pip` installed.
Install the following pip packages:
- `pygame-ce` (>= 2.5.7)
- `pynput` (>= 1.8.0)

In your recording software (I use OBS for example) add a Window Capture, select the gsbrd window and add a Chromakey filter to make the background transparent.

**Known Issues**
- You might experience some issues on Wayland with capturing keys globally
