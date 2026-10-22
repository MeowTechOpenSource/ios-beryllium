# Driver-independent foundations

`transport.[ch]` implements HTC RX envelope validation for the WCN3990 Wi-Fi port
and APR v0 packet encoding/decoding for the audio DSP port. These functions are
freestanding, handle unaligned input without packed casts, and reject malformed
lengths before exposing payloads. The HTC endpoint-zero negotiation state machine validates READY credits and CONNECT_SERVICE responses, including service/endpoint matching and retry after firmware rejection. Calls must be serialized by the future driver. HTC accepts bus padding after the declared frame;
APR expects a single exact packet. Final audio command results are checked against both token and original opcode; an ACCEPTED response is not treated as completion. APR encoder input payload must not overlap its
output buffer. Neither module is connected to a firmware or hardware transport yet.

`display.h` supplies the 1080×2246 viewport mapping and BGRA test pattern used by
the Poco-only kernel overlay. Pattern drawing is selected with `beryllium_fbtest=1`;
this explicitly mutes console drawing so the pattern remains visible. Do not use
that flag for ordinary text-based bring-up. It is CPU rendering, not Adreno work.

Host checks:

```
clang -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined ports/beryllium/support/transport.c tools/test-beryllium-transport.c -o /tmp/beryllium-transport
/tmp/beryllium-transport
clang -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined tools/test-beryllium-display.c -o /tmp/beryllium-display
/tmp/beryllium-display
```

Wire references and missing driver dependencies are in ../STATUS.md.
