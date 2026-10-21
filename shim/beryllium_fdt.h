#pragma once
#include <stddef.h>
#include <stdint.h>

struct beryllium_fb {
    uint64_t base, size;
};

/* No framebuffer address fallback: require matching device and explicit
 * simple-framebuffer metadata in /chosen. Returns zero on malformed input. */
int beryllium_framebuffer(const void *blob, size_t available,
                         struct beryllium_fb *out);
