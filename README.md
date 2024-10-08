# mmng-ui

A TUI (text user interface) frontend for `multimon-ng`.

`mmng-ui` will listen on a chosen UDP port for raw streams from software like SDR++, use `multimon-ng` to decode it,
and show you POCSAG messages in a wonderful text interface.

## Table of contents

<!-- TOC -->
* [mmng-ui](#mmng-ui)
  * [Table of contents](#table-of-contents)
  * [Purpose](#purpose)
  * [Installation](#installation)
  * [How to use it](#how-to-use-it)
  * [Supported Python versions](#supported-python-versions)
<!-- TOC -->


## Purpose

Why not?  I know there are other frontends out there, but I haevn't seen any for use in a text console.

I also wanted to learn both [Rich](https://github.com/Textualize/rich) and [Textual](https://github.com/Textualize/textual).

## Installation

The recommended way to install `mmng-ui` is to use [pipx](https://pipx.pypa.io/stable/).

After getting `pipx` installed, simply run:

```shell
username@host:~$ pipx install mmng-ui
```

Please [don't use pip system-wide](https://docs.python.org/3.11/installing/index.html#installing-into-the-system-python-on-linux).

You can of course also install it using classic virtualenvs.

## How to use it

See `mmng-ui --help` for CLI options.

Run `mmng-ui`, and you'll be greeted with this screen:

![screenshot](https://raw.githubusercontent.com/lingfish/mmng-ui/refs/heads/main/docs/initial%20screen.png)

Notice in the status pane, it says "Receiver: idle" -- it is now listening for UDP packets sent to the default port
of 8888.

Now go to your favourite SDR application, and send to where `mmng-ui` is running.  Make sure it is the right sample
rate that `multimon-ng` likes, 22050 Hz.  It probably helps to send mono too.

Alpha POCSAG messages will soon display in the top pane.  The bottom pane will show the raw output from `multimon-ng`,
as well as any errors or issues with decoding.

The status panel shows any incoming connections.  Receiver will transition between the following states:

| Receiver state | Description                                     |
|----------------|-------------------------------------------------|
| idle           | No UDP traffic yet seen, or seen in 5 seconds   |
| receiving      | Actively receiving a decode from `multimon-ng`  |
| waiting        | Traffic is coming in, but nothing to be decoded |

Just below the status panel is a sparkline -- this updates on each decode, and reflects character length of said
decode.

Underneath the log window in another sparkline, and this shows messages per second, for the last minute.

The footer shows available keyboard choices to quit the app, show a help screen, and clear all logging panes.

The mouse will also work!

### JSON mode

`mmng-ui` will attempt to auto-detect the output format from `multimon-ng`, and if it looks like JSON, it'll use it.

JSON output isn't yet in `multimon-ng`, but I have a working
fork [here](https://github.com/lingfish/multimon-ng/tree/add-json).

## Example screenshot

Here's what a screen full of decodes might look like:

![screenshot](https://raw.githubusercontent.com/lingfish/mmng-ui/refs/heads/main/docs/working%20screen.png)

## Supported Python versions

`mmng-ui` supports Python 3.9 and newer.
