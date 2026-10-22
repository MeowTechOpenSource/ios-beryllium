/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include "../ports/beryllium/support/display.h"
int main(void) {
    struct beryllium_viewport v;
    assert(!beryllium_viewport_init(&v,1080,2246,0));
    assert(v.offset_x==22 && v.offset_y==95 && v.logical_height==2436);
    int x=beryllium_axis_fixed(INT_MAX,v.width,v.offset_x,v.logical_width);
    assert(x==beryllium_axis_fixed(1079,v.width,v.offset_x,v.logical_width));
    int y=beryllium_axis_fixed(INT_MAX,v.height,v.offset_y,v.logical_height);
    assert(y==beryllium_axis_fixed(2245,v.height,v.offset_y,v.logical_height));
    assert(!beryllium_viewport_init(&v,1080,2246,1));
    assert(v.logical_height==2246 && v.offset_y==0);
    assert(beryllium_axis_fixed(INT_MIN,v.height,0,v.height)==0);
    assert(beryllium_axis_fixed(2246,v.height,0,v.height)<65536);
    assert(beryllium_axis_fixed(0,0,0,1)<0);
    assert(beryllium_viewport_init(&v,0,2246,0)<0);
    uint32_t p[4*12+2];
    for (unsigned i=0;i<50;i++) p[i]=0x12345678;
    assert(!beryllium_display_pattern(p+1,4*12*4,10,4,48));
    assert(p[0]==0x12345678 && p[49]==0x12345678);
    for (unsigned row=0;row<4;row++)
        assert(p[1+row*12+10]==0x12345678 && p[1+row*12+11]==0x12345678);
    assert(beryllium_display_pattern(p,0,10,4,48)<0);
    assert(beryllium_display_pattern(p,sizeof(p),10,4,0)<0);
    assert(beryllium_display_pattern(p,sizeof(p),10,4,39)<0);
    puts("Poco viewport / BGRA pattern: boundaries, native mode, row padding and canaries passed");
}
