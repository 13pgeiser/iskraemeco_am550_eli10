Publishing Iskraemeco AM550 elecricity meter over Prometheus
############################################################

:date: 2026-01-11 19:00
:modified: 2026-01-11 19:00
:tags: AM550, dlms, cosem, prometheus
:authors: Pascal Geiser
:summary: Decoding the UART stream from the power meter and exposing it to Prometheus

.. contents::

Introduction
************

Most of the elecricity meters are exposing the power meters in ascii over an RJ11 uart interface.
Sadly, in my case, it seems that my elecricity company configured it to send data in binary form.
It looks like `IEC 62056-21 <https://en.wikipedia.org/wiki/IEC_62056>`__ mode e (HDLC?)

The serial interface send binary data over uart @ 115200bps, 1 stop bit, no parity.
Each frame ends with a 16 bits CRC (CRC16-CCIT reversed)

Parsing
*******

`See am550.py <https://github.com/13pgeiser/iskraemeco_am550_eli10/blob/master/am550.py>`__

The parser takes the whole frame and starts computing the CRC16-CCIT over the whole frame minus
the last 2 bytes which are compared with the result. If they match, the parser continues otherwise,
the frame is completely skipped.

The processing continues at parse_cosem_frame which tries to decode the frame. The first 16 bytes are
skipped, I could not find really what they were representing. Then, a timestamp is decoded and finally
the meters themseleves (encoded using ASN.1).

