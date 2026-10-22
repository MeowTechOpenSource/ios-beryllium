/* SPDX-License-Identifier: MIT
 * Pure display helpers shared by the Poco kernel overlay and host tests.
 */
#pragma once
#include <stddef.h>
#include <stdint.h>
struct beryllium_viewport {
    int width, height, logical_width, logical_height, offset_x, offset_y;
};
static inline int beryllium_viewport_init(struct beryllium_viewport *v,
                                         unsigned w, unsigned h, int native)
{
    if (!v || !w || !h || w>16384 || h>16384) return -1;
    v->width=(int)w; v->height=(int)h;
    v->logical_width=(!native && w<=1125 && h<=2436) ? 1125 : (int)w;
    v->logical_height=(!native && w<=1125 && h<=2436) ? 2436 : (int)h;
    v->offset_x=(v->logical_width-v->width)/2;
    v->offset_y=(v->logical_height-v->height)/2;
    return 0;
}
static inline int beryllium_axis_fixed(int value, int extent, int offset, int logical)
{
    if (extent<=0 || logical<=0 || extent>16384 || logical>16384 ||
        offset<0 || offset>logical || extent>logical-offset) return -1;
    value=value<0 ? 0 : (value>=extent ? extent-1 : value);
    return (int)(((int64_t)value+offset)*65536/logical);
}
/* BGRA/XRGB little-endian words. Draw only visible pixels; preserve row padding. */
static inline int beryllium_display_pattern(volatile uint32_t *pixels, size_t bytes,
                                            unsigned w, unsigned h, unsigned stride)
{
    if (!pixels || !w || !h || w>16384 || h>16384 || stride%4 ||
        stride/4<w || h>bytes/stride) return -1;
    const uint32_t colors[8]={0xffffffff,0xffffff00,0xff00ffff,0xff00ff00,
                              0xffff00ff,0xffff0000,0xff0000ff,0xff000000};
    for (unsigned y=0;y<h;y++)
        for (unsigned x=0;x<w;x++)
            pixels[(size_t)y*(stride/4)+x]=(x==0 || y==0 || x==w-1 || y==h-1)
                ? 0xffffffff : colors[(size_t)x*8/w];
    return 0;
}
