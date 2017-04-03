import dbus

sysbus = dbus.SystemBus()
sysdobj = sysbus.get_object("org.freedesktop.systemd1", "/org/freedesktop/systemd1")
systemd_interface = dbus.Interface(sysdobj, "org.freedesktop.systemd1.Manager") # We can now call systemd methods directly.