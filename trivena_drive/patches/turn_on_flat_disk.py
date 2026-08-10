import trivena_framework as trivena


def execute():
    settings = trivena.get_single("Drive Disk Settings")
    settings.flat = True
    settings.save()
