/* SPDX-License-Identifier: MIT */
#include "transport.h"
static uint16_t get16(const uint8_t *p) { return p[0] | (uint16_t)p[1] << 8; }
static uint32_t get32(const uint8_t *p) { return get16(p) | (uint32_t)get16(p+2) << 16; }
static void put16(uint8_t *p, uint16_t v) { p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); }
static void put32(uint8_t *p, uint32_t v) { put16(p,(uint16_t)v); put16(p+2,(uint16_t)(v>>16)); }
int beryllium_htc_decode(const void *data, size_t n, struct beryllium_htc_rx *out)
{
    if (!data || !out || n < 8) return -1;
    const uint8_t *p=data;
    size_t length=get16(p+2), trailer=(p[1]&2) ? p[4] : 0;
    if (p[0]>=9 || length>4096 || length>n-8 || trailer>length) return -1;
    /* Trailer records are id, length, two pad bytes, value; validate before exposing bytes. */
    size_t pos=8+length-trailer, end=8+length;
    while (pos<end) {
        if (end-pos<4 || p[pos+1]>end-pos-4) return -1;
        pos += 4+p[pos+1];
    }
    *out=(struct beryllium_htc_rx){p[0],p+8,p+8+length-trailer,
                                  length-trailer,trailer,8+length};
    return 0;
}
int beryllium_apr_decode(const void *data, size_t n, struct beryllium_apr *out)
{
    if (!data || !out || n<20) return -1;
    const uint8_t *p=data;
    uint16_t field=get16(p), length=get16(p+2);
    size_t header=((field>>4)&15)*4;
    if ((field&15) || (field&0xfc00) || header<20 || header>length || length!=n) return -1;
    *out=(struct beryllium_apr){(uint8_t)((field>>8)&3),p[4],p[5],p[8],p[9],
        get16(p+6),get16(p+10),get32(p+12),get32(p+16),p+header,n-header};
    return 0;
}
size_t beryllium_apr_encode(void *data, size_t n, const struct beryllium_apr *m)
{
    if (!data || !m || m->type>3 || m->payload_size>65535-20 ||
        n<20+m->payload_size || (m->payload_size && !m->payload)) return 0;
    uint8_t *p=data;
    put16(p,(uint16_t)(0x50 | m->type<<8)); put16(p+2,(uint16_t)(20+m->payload_size));
    p[4]=m->src_service; p[5]=m->src_domain; put16(p+6,m->src_port);
    p[8]=m->dst_service; p[9]=m->dst_domain; put16(p+10,m->dst_port);
    put32(p+12,m->token); put32(p+16,m->opcode);
    for (size_t i=0;i<m->payload_size;i++) p[20+i]=m->payload[i];
    return 20+m->payload_size;
}
