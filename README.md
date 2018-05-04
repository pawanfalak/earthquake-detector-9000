# earthquake-recognition


## Dataset

1. Retrieving and processing the data:

https://github.com/jamesaud/seismic-analysis-toolbox

The idea is to feed in Spectrogram images to a convolutional neural network in order to detect earthquakes.

The data is too large to be held on github, but you can download the data with the toolbox. I will make my dataset available in the future (on Dropbox or something).

On my machine I have roughly 4 million waveforms downloaded!

## Code

Written in Pytorch.

If you are familar with Pytorch, the main code will look familiar:

https://github.com/jamesaud/earthquake-detector-9000/blob/neuralnet/main.py


## Visualization

Run `docker-compose up` to get Tensorboard running on localhost:6000

The code in main is configured to write to the folder for visualization.
