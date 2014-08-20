from distutils.core import setup

setup(name='xprojedit',
      version='0.1',
      description='convenient methods for xcode project manipulation.',
      author='David Marte',
      author_email='redesigndavid@gmail.com',
      url='http://www.redesigndavid.com/?tags=xprojedit',
      py_modules=['xprojedit.classes', 'xprojedit.interface', 'xprojedit.__init__'],
      package_dir={'': 'python'},
      scripts=['bin/xprojedit'],
      )
