#import <AppKit/AppKit.h>
#import <Metal/Metal.h>
#import <QuartzCore/CAMetalLayer.h>

int main(void) {
    @autoreleasepool {
        NSApplication *application = [NSApplication sharedApplication];
        CAMetalLayer *layer = [CAMetalLayer layer];
        id<MTLDevice> device = MTLCreateSystemDefaultDevice();
        if (application == nil || layer == nil) {
            return 1;
        }
        layer.device = device;
        return 0;
    }
}
