#!/usr/bin/env python3
"""Check the real patched sampler against lock/lifetime fixtures.

Pass the patched XNU osfmk/kern/exception.c. The extracted production function
is compiled with host stubs that reject paging, allocation and output under the
task lock, and check balanced map references and bounded thread enumeration.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
args = parser.parse_args()
s = args.source.read_text()
a = s.index('void\nsweet_sample_task(')
b = s.index('\n#endif /* ARM64_BOARD_CONFIG_SWEET */', a)
function = s[a:b]
fixture = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
struct state { uint64_t pc,lr,sp,fp; int valid; };
typedef struct state arm_saved_state_t;
struct thread { struct state ss; struct thread *next; };
typedef struct thread *thread_t;
struct map { int refs; };
typedef struct map *vm_map_t;
struct task { struct thread *threads; uint64_t mach_header_vm_address; struct map map; };
typedef struct task *task_t;
struct region { uint64_t sr_slide; };
typedef struct region *vm_shared_region_t;
static int locked, outputs, reads, allocations, fail_alloc, fault_read, region_refs;
static struct region region = { 0x4000 };
#define Z_WAITOK 1
#define Z_ZERO 2
#define KERN_SUCCESS 0
#define queue_iterate(q,t,type,link) for ((t)=*(q); (t); (t)=(t)->next)
static void *kalloc_data(size_t n, int flags) {
    (void)flags; assert(!locked); if (fail_alloc) return NULL;
    allocations++; return calloc(1,n);
}
static void kfree_data(void *p,size_t n) {
    (void)n; assert(!locked); assert(allocations>0); allocations--; free(p);
}
static int output(const char *fmt,...) {
    (void)fmt; assert(!locked); outputs++; return 0;
}
static int format(char *p,size_t n,const char *fmt,...) {
    assert(!locked); va_list ap; va_start(ap,fmt); int r=vsnprintf(p,n,fmt,ap); va_end(ap); return r;
}
#define printf output
#define snprintf format
static void task_lock(task_t t) { (void)t; assert(!locked); locked=1; }
static void task_unlock(task_t t) { (void)t; assert(locked); locked=0; }
static vm_map_t get_task_map(task_t t) { assert(locked); return &t->map; }
static void vm_map_reference(vm_map_t m) { assert(locked); m->refs++; }
static void vm_map_deallocate(vm_map_t m) { assert(!locked); assert(m->refs>0); m->refs--; }
static vm_shared_region_t vm_shared_region_get(task_t t) { (void)t; assert(!locked); region_refs++; return &region; }
static void vm_shared_region_deallocate(vm_shared_region_t r) { (void)r; assert(region_refs>0); region_refs--; }
static arm_saved_state_t *find_user_regs(thread_t t) { assert(locked); return &t->ss; }
static bool is_saved_state64(arm_saved_state_t *s) { return s->valid; }
#define get_saved_state_pc(s) ((s)->pc)
#define get_saved_state_lr(s) ((s)->lr)
#define get_saved_state_sp(s) ((s)->sp)
#define get_saved_state_fp(s) ((s)->fp)
static int vm_map_read_user(vm_map_t m,uint64_t fp,void *out,size_t n) {
    assert(!locked); assert(m->refs>0); assert(n==16); reads++;
    if (fault_read) return 1;
    uint64_t frame[2]={fp,0x1234}; memcpy(out,frame,16); return 0;
}
'''
main = r'''
int main(void) {
    struct thread threads[80]={0}; struct task t={0}; t.threads=threads;
    for(int i=0;i<80;i++) { threads[i].ss.valid=1; threads[i].ss.fp=0x1000; threads[i].next=i<79?&threads[i+1]:NULL; }
    sweet_sample_task("lsd",102,&t);
    assert(reads==64 && outputs==66); /* header, 64 threads, truncation */
    assert(!locked && !t.map.refs && !allocations && !region_refs);
    outputs=reads=0; fault_read=1;
    sweet_sample_task("lsd",102,&t);
    assert(reads==64 && outputs==66); /* fault terminates each walk */
    assert(!locked && !t.map.refs && !allocations && !region_refs);
    outputs=reads=0; fault_read=0; threads[0].ss.valid=0; threads[1].next=NULL;
    sweet_sample_task("lsd",102,&t);
    assert(reads==1 && outputs==2); /* invalid state skipped */
    assert(!locked && !t.map.refs && !allocations && !region_refs);
    outputs=reads=0; fail_alloc=1;
    sweet_sample_task("lsd",102,&t);
    assert(reads==0 && outputs==1);
    assert(!locked && !t.map.refs && !allocations && !region_refs);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='beryllium-sampler-') as td:
    src = Path(td)/'fixture.c'
    exe = Path(td)/'fixture'
    src.write_text(fixture+function+main)
    subprocess.run(['cc','-std=c11','-Wno-format','-fsanitize=address,undefined',str(src),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('Sampler lock/lifetime, truncation, invalid-state and read/allocation-failure fixtures passed')
