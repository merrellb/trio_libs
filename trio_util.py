import traceback
import trio

def cancellable_factory(func_name, instance):
    func = getattr(instance, func_name)
    async def scope_func():
        try:
            print(func_name, " {}: started".format(instance.ident))
            with trio.open_cancel_scope() as cancel_scope:
                instance.cancel_scopes.append(cancel_scope)
                await func()
        except Exception as exc:
            traceback.print_exc()
            print(func_name, " {}: crashed: {!r}".format(instance.ident, exc))
            instance.shutdown.set()
        print(func_name, " {}: stopped".format(instance.ident))
    return scope_func

# Simple connection management
class AwaitableSet(set):

    def __init__(self, *args, **kwargs):
        set.__init__(self, *args, **kwargs)
        self.empty = trio.Event()
        self.empty.set()

    def add(self, *args, **kwargs):
        set.add(self, *args, **kwargs)
        self.empty.clear()

    def remove(self, *args, **kwargs):
        set.remove(self, *args, **kwargs)
        if not self:
            self.empty.set()

    async def shutdown_all(self):
        async with trio.open_nursery() as nursery:            
            for conn in self:
                conn.shutdown.set()
                nursery.spawn(conn.do_shutdown)
        await self.empty.wait()
