# PGI / JCNS Sample and Measurement Database
[![build status](https://iffgit.fz-juelich.de/Scientific-IT-Systems/SampleDB/badges/master/build.svg)](https://iffgit.fz-juelich.de/Scientific-IT-Systems/SampleDB/commits/master) [![coverage report](https://iffgit.fz-juelich.de/Scientific-IT-Systems/SampleDB/badges/master/coverage.svg)](https://iffgit.fz-juelich.de/Scientific-IT-Systems/SampleDB/commits/master)

To use locally simply install the dependencies via

```
pip install -r requirements.txt
```

and then run

```
python -m sampledb run
```

This will start a server at [http://localhost:8000](http://localhost:8000). You can also run `python demo.py` for some pre-existing instruments, actions and samples.

The current test deployment is available at [https://docker.iff.kfa-juelich.de/sampledb/](https://docker.iff.kfa-juelich.de/sampledb/).
