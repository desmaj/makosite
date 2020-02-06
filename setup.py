from setuptools import find_packages
from setuptools import setup


VERSION = '0.3.0'
DESCRIPTION = """
Simple website builder using mako templates.


"""

setup(
    name='makosite',
    version=VERSION,
    description=DESCRIPTION.strip().splitlines()[0],
    long_description=DESCRIPTION.strip(),
    classifiers=[],
    keywords='',
    author='Matthew Desmarais',
    author_email='matthew.desmarais@gmail.com',
    url='https://github.com/desmaj/makosite',
    license='GPLv3',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'beautifulsoup4>=4.8.2',
        'Click>=7.0',
        'Mako>=1.1.0',
    ],
    entry_points="""
    [console_scripts]
    mksite = makosite.run:main
    mksite-import = makosite.importer:main
    """,
)
