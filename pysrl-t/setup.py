from setuptools import setup, find_packages

setup(
    name='pysrl-t',
    version='0.1.0',
    description='Python implementation of SRL-T webgraph generator',
    author='SRL-T Contributors',
    packages=find_packages(),
    install_requires=[
        'Pillow>=9.0.0',
        'numpy>=1.20.0',
        'scipy>=1.7.0',
        'scikit-image>=0.19.0',
    ],
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            'generate-webgraph=pysrl_t.generate_graph:main',
        ],
    },
)

