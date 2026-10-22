/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../ports/beryllium/support/transport.h"
int main(void) {
    struct beryllium_htc_rx rx;
    /* Endpoint 1, four payload bytes, one eight-byte trailer record. */
    unsigned char htc[]={1,2,12,0,8,0,0,0,0xaa,0xbb,0xcc,0xdd,1,4,0,0,1,2,0,0};
    for (size_t i=0;i<sizeof(htc);i++) assert(beryllium_htc_decode(htc,i,&rx)<0);
    assert(!beryllium_htc_decode(htc,sizeof(htc),&rx));
    assert(rx.payload_size==4 && rx.trailer_size==8 && rx.payload[2]==0xcc);
    htc[13]=5; assert(beryllium_htc_decode(htc,sizeof(htc),&rx)<0); htc[13]=4;
    htc[0]=9; assert(beryllium_htc_decode(htc,sizeof(htc),&rx)<0); htc[0]=1;
    htc[4]=13; assert(beryllium_htc_decode(htc,sizeof(htc),&rx)<0);
    unsigned char body[]={0x78,0x56,0x34,0x12};
    struct beryllium_apr m={2,3,5,7,4,0x1234,0xabcd,0x11223344,0x55667788,body,4}, decoded;
    unsigned char storage[80]; memset(storage,0x5a,sizeof(storage));
    unsigned char *frame=storage+1; /* deliberately unaligned */
    assert(beryllium_apr_encode(frame,23,&m)==0);
    assert(beryllium_apr_encode(frame,24,&m)==24);
    const unsigned char expected[]={0x50,2,24,0,3,5,0x34,0x12,7,4,0xcd,0xab,0x44,0x33,0x22,0x11,0x88,0x77,0x66,0x55,0x78,0x56,0x34,0x12};
    assert(!memcmp(frame,expected,24) && storage[0]==0x5a && storage[25]==0x5a);
    for (size_t i=0;i<24;i++) assert(beryllium_apr_decode(frame,i,&decoded)<0);
    assert(!beryllium_apr_decode(frame,24,&decoded));
    assert(decoded.token==m.token && decoded.opcode==m.opcode && decoded.payload_size==4);
    frame[0]|=1; assert(beryllium_apr_decode(frame,24,&decoded)<0); frame[0]&=~1;
    frame[1]|=4; assert(beryllium_apr_decode(frame,24,&decoded)<0);
    unsigned char response[]={0x88,0x77,0x66,0x55,0,0,0,0};
    m.type=1; m.opcode=0x110e8; m.payload=response; m.payload_size=8;
    assert(beryllium_apr_encode(frame,32,&m)==28);
    uint32_t status=0xdeadbeef;
    assert(!beryllium_apr_result(frame,28,m.token,0x55667788,&status) && status==0);
    assert(beryllium_apr_result(frame,28,m.token+1,0x55667788,&status)<0);
    assert(beryllium_apr_result(frame,28,m.token,1,&status)<0);
    m.opcode=0x100be; assert(beryllium_apr_encode(frame,32,&m)==28);
    assert(beryllium_apr_result(frame,28,m.token,0x55667788,&status)<0);
    struct beryllium_htc_session session={0};
    unsigned char ready[]={0,0,8,0,0,0,0,0,1,0,8,0,0,1,9,0};
    unsigned char request[8];
    assert(!beryllium_htc_connect(&session,0x100,0,request,8));
    assert(!beryllium_htc_control(&session,ready,sizeof(ready)));
    assert(session.state==BERYLLIUM_HTC_READY && session.credits==8 && session.credit_size==256);
    assert(beryllium_htc_control(&session,ready,sizeof(ready))<0); /* duplicate READY */
    assert(!beryllium_htc_connect(&session,0x100,0x900,request,8)); /* over-allocation */
    assert(!beryllium_htc_connect(&session,0x100,0,request,7));
    assert(beryllium_htc_connect(&session,0x100,0,request,8)==8);
    const unsigned char connect_expected[]={2,0,0,1,0,0,0,0};
    assert(!memcmp(request,connect_expected,8));
    unsigned char reply[]={0,0,8,0,0,0,0,0,3,0,0,1,0,2,0,4};
    reply[10]=1; assert(beryllium_htc_control(&session,reply,sizeof(reply))<0); reply[10]=0;
    assert(session.state==BERYLLIUM_HTC_CONNECTING);
    reply[13]=9; assert(beryllium_htc_control(&session,reply,sizeof(reply))<0); reply[13]=2;
    assert(!beryllium_htc_control(&session,reply,sizeof(reply)));
    assert(session.state==BERYLLIUM_HTC_BOUND && session.endpoint==2 && session.max_message==1024);
    /* Deterministic malformed input sweep under ASan/UBSan. */
    unsigned char fuzz[4097]; uint32_t seed=1;
    for (unsigned t=0;t<20000;t++) {
        seed=seed*1664525u+1013904223u; size_t n=seed%sizeof(fuzz);
        for (size_t i=0;i<n;i++) { seed=seed*1664525u+1013904223u; fuzz[i]=(unsigned char)(seed>>24); }
        (void)beryllium_htc_decode(fuzz,n,&rx);
        (void)beryllium_apr_decode(fuzz,n,&decoded);
    }
    puts("HTC RX / APR framing: wire fixtures, truncations, unaligned buffers and canaries passed");
}
