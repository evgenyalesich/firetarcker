from setuptools import setup
from Cython.Build import cythonize
import os

# py_files = os.listdir("FireStorm/modules")
# py_files = list(filter(lambda name: name.endswith(".py"), py_files))
# print(py_files)

setup(
    ext_modules=cythonize(
        [
            "FireStorm/modules/FireStorm.py",
            "FireStorm/modules/update_installer.py",
            "FireStorm/modules/uploader.py",
            "FireStorm/modules/app_gui.py",
            "FireStorm/modules/http_client.py",
            "FireStorm/modules/log_in_form.py",
            "FireStorm/modules/main_window.py",
            "FireStorm/modules/polygons.py",
            "FireStorm/modules/update_progressbar.py",
            "FireStorm/modules/views.py",
            "FireStorm/modules/paths_checker.py",
        ],
        force=True,
    )
)
