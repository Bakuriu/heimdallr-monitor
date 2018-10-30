from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='heimdallr',
    version='0.2.0',
    author='Giacomo Alzetta',
    author_email='giacomo.alzetta+heimdallr@gmail.com',
    scripts=['heimdallr'],
    license='MIT',
    description='Monitor CPU,GPU,RAM & temperatures of the system or a process',
    long_description=long_description,
    keywords='monitoring',
    url='https://github.com/Bakuriu/heimdallr-monitor',
    project_urls={
        'Bug Tracker': 'https://github.com/Bakuriu/heimdallr-monitor/issues',
        'Source Code': 'https://github.com/Bakuriu/heimdallr-monitor',
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'Topic :: System :: Monitoring',
        'Topic :: Utilities',
    ]
)
