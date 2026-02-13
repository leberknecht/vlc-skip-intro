from setuptools import setup, find_packages

setup(
    name="vlc-skip-intro",
    version="1.0.0",
    description="Detect and store intro timestamps in video files",
    author="",
    packages=find_packages(),
    install_requires=[
        "opencv-python>=4.8.0",
        "scikit-image>=0.21.0",
        "imagehash>=4.3.1",
        "click>=8.1.0",
        "numpy>=1.24.0",
        "Pillow>=10.0.0",
    ],
    entry_points={
        "console_scripts": [
            "vlc-skip-intro=vlc_skip_intro.cli:main",
        ],
    },
    python_requires=">=3.8",
)
