/* SPDX-License-Identifier: MIT
 * Bounded wire codecs for future WCN3990 HTC / ADSP APR transports.
 * No MMIO, DMA, firmware loading, association, or audio playback here.
 */
#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
struct beryllium_htc_rx {
    uint8_t endpoint;
    const uint8_t *payload, *trailer;
    size_t payload_size, trailer_size, frame_size;
};
/* Input is one RX frame; trailing transfer padding is allowed. */
int beryllium_htc_decode(const void *, size_t, struct beryllium_htc_rx *);
enum beryllium_htc_state { BERYLLIUM_HTC_RESET, BERYLLIUM_HTC_READY,
                            BERYLLIUM_HTC_CONNECTING, BERYLLIUM_HTC_BOUND };
struct beryllium_htc_session {
    enum beryllium_htc_state state;
    uint16_t credits, credit_size, service, max_message;
    uint8_t max_endpoints, endpoint;
};
/* Process endpoint-zero READY/CONNECT_RESPONSE frames. No actual bus I/O. */
int beryllium_htc_control(struct beryllium_htc_session *, const void *, size_t);
/* Emit the eight-byte CONNECT_SERVICE message payload, then await a response. */
size_t beryllium_htc_connect(struct beryllium_htc_session *, uint16_t service,
                            uint16_t flags, void *, size_t);
struct beryllium_apr {
    uint8_t type, src_service, src_domain, dst_service, dst_domain;
    uint16_t src_port, dst_port;
    uint32_t token, opcode;
    const uint8_t *payload;
    size_t payload_size;
};
int beryllium_apr_decode(const void *, size_t, struct beryllium_apr *);
/* Accept only a final BASIC_RSP_RESULT for this token and original command. */
int beryllium_apr_result(const void *, size_t, uint32_t token,
                        uint32_t command, uint32_t *status);
/* Emits APR v0, 20-byte header, followed by payload. Returns 0 on rejection. */
size_t beryllium_apr_encode(void *, size_t, const struct beryllium_apr *);
#ifdef __cplusplus
}
#endif
