import trio

def cancellable_factory(func_name, instance):
    func = getattr(instance, func_name)
    async def scope_func():
        try:
            print(func_name, " {}: started".format(instance.ident))
            await func()
        except Exception as exc:
            print(func_name, " {}: crashed: {!r}".format(instance.ident, exc))
            await instance.shutdown()
        except trio.Cancelled:
            print(func_name, " {}: cancelled".format(instance.ident))
        print(func_name, " {}: stopped".format(instance.ident))
    return scope_func
