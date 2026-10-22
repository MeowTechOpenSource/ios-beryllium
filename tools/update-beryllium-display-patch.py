#!/usr/bin/env python3
"""Regenerate the Poco-only graphics/HID overlay from the audited 0081 sources."""
from pathlib import Path
import difflib
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'research/upstream-0081/xnu'
changes=[]
name='iokit/Kernel/arm/BerylliumDisplay.h'
changes.append((name,'',(ROOT/'ports/beryllium/support/display.h').read_text()))
name='iokit/Kernel/arm/SweetFramebuffer.cpp'
s=(base/name).read_text()
old='#include <pexpert/pexpert.h>'
assert old in s
n=s.replace(old,old+'\n#include "BerylliumDisplay.h"',1)
old='\tfVsync->setTimeoutUS(SWEET_FB_VSYNC_US);'
assert n.count(old)>=1
n=n.replace(old,'''\tint pattern = 0;
\tPE_parse_boot_argn("beryllium_fbtest", &pattern, sizeof(pattern));
\tif (pattern) {
\t\tsweet_console_muted = 1; /* explicit test mode; panics still draw */
\t\tint result = beryllium_display_pattern((volatile uint32_t *)fPixels,
\t\t    (size_t)fRowBytes * fHeight, fWidth, fHeight, fRowBytes);
\t\tIOLog("BERYLLIUM graphics: pattern result=%d %ux%u stride=%u\\n",
\t\t    result, fWidth, fHeight, fRowBytes);
\t}
'''+old,1)
changes.append((name,s,n))
name='iokit/Kernel/arm/hid/SweetHID.cpp'
s=(base/name).read_text();n=s.replace('#include <pexpert/pexpert.h>','#include <pexpert/pexpert.h>\n#include "../BerylliumDisplay.h"',1)
n=n.replace('int fLogicalW, fLogicalH, fOffX, fOffY;','int fLogicalW, fLogicalH, fOffX, fOffY, fPhysicalW, fPhysicalH;',1)
old='''\tfLogicalW = native ? 1080 : 1125;
\tfLogicalH = native ? 2400 : 2436;
\tfOffX = (fLogicalW - 1080) / 2;
\tfOffY = (fLogicalH - 2400) / 2;'''
new='''\tPE_Video video = {};
\tPE_current_console(&video);
\tstruct beryllium_viewport view;
\tif (video.v_width > 16384 || video.v_height > 16384 ||
\t    beryllium_viewport_init(&view, (unsigned)video.v_width,
\t    (unsigned)video.v_height, native)) return false;
\tfPhysicalW = view.width;
\tfPhysicalH = view.height;
\tfLogicalW = view.logical_width;
\tfLogicalH = view.logical_height;
\tfOffX = view.offset_x;
\tfOffY = view.offset_y;'''
assert n.count(old)==1;n=n.replace(old,new)
n=n.replace('x > 1079 ? 1079 : x','x >= fPhysicalW ? fPhysicalW - 1 : x').replace('y > 2399 ? 2399 : y','y >= fPhysicalH ? fPhysicalH - 1 : y')
n=n.replace('((int64_t)(x + fOffX) << 16) / fLogicalW','beryllium_axis_fixed(x, fPhysicalW, fOffX, fLogicalW)').replace('((int64_t)(y + fOffY) << 16) / fLogicalH','beryllium_axis_fixed(y, fPhysicalH, fOffY, fLogicalH)')
n=n.replace('x > 1079 - SWEET_TOUCH_EDGE_PX','x > fPhysicalW - 1 - SWEET_TOUCH_EDGE_PX').replace('y > 2399 - SWEET_TOUCH_EDGE_PX','y > fPhysicalH - 1 - SWEET_TOUCH_EDGE_PX')
changes.append((name,s,n))
name='pexpert/arm/pe_serial.c'
s=(base/name).read_text()
old='fbcon_transmit_data(uint8_t c)\n{'
assert s.count(old)==1
n=s.replace(old,old+"\n\textern int sweet_console_muted;\n\tif (sweet_console_muted && !panic_active()) return;",1)
changes.append((name,s,n))
patch=''.join(''.join(difflib.unified_diff(s.splitlines(True),n.splitlines(True),fromfile='a/'+p if s else '/dev/null',tofile='b/'+p)) for p,s,n in changes)
(ROOT/'ports/beryllium/xnu/0084-beryllium-display-profile.patch').write_text(patch)
