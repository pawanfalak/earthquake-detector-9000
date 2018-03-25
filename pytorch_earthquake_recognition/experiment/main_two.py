import torch
from torch import nn
import torch.optim as optim
from torch.autograd import Variable
from torch.utils.data import DataLoader
from loaders.multiple_loader import SpectrogramMultipleDataset
import models
from pycrayon import CrayonClient
import os
from datetime import datetime


def to_np(x):
    return x.data.cpu().numpy()

IMG_PATH = os.path.join(os.getcwd(), 'spectrograms')
IMG_EXT = '.png'
BATCH_SIZE = 512

# variables
NET = models.mnist_simple

MODEL_PATH = f'checkpoints/{NET.__name__}'


# Visualize
cc = CrayonClient(hostname="0.0.0.0")
summary = cc.create_experiment(f"/{NET.__name__}/trial-{datetime.now()}")

# Dataset
dataset_train = SpectrogramMultipleDataset(IMG_PATH,
                                   transform=NET.transformations['train'])

dataset_test = SpectrogramMultipleDataset(IMG_PATH,
                                  transform=NET.transformations['test'],
                                  test=True)


# Data Loader
train_loader = DataLoader(dataset_train,
                          batch_size=BATCH_SIZE,
                          shuffle=True,
                          num_workers=10,
                          pin_memory=True  # CUDA only
                          )

test_loader = DataLoader(dataset_test,
                         batch_size=BATCH_SIZE,
                         num_workers=10,
                         pin_memory=True
                         )

# To test the  accuracy against the training dataset
train_test_loader = DataLoader(dataset_train,
                          batch_size=BATCH_SIZE,
                          shuffle=True,
                          num_workers=10,
                          pin_memory=True
                          )


# Setup Net
net = NET().cuda()
optimizer = optim.Adam(net.parameters()) # optim.SGD(net.parameters(), lr=.005, momentum=.9) #
criterion = nn.CrossEntropyLoss().cuda()


def guess_labels(batches):
    """
    Tries to guess labels based on data
    """
    dataiter = iter(test_loader)

    for i in range(batches):
        images, labels = dataiter.next()
        images = [Variable(input).cuda() for image in images]

        # print images
        print('GroundTruth: ', ' '.join('%5s' % labels[j] for j in range(BATCH_SIZE)))

        outputs = net(images)

        _, predicted = torch.max(outputs.data, 1)

        print('Predicted:   ', ' '.join('%5s' % predicted[j] for j in range(BATCH_SIZE)))
        print()


def class_evaluation(net, copy_net=False):
    """
    Tests how accurate each class is in the net - noise vs local vs nonlocal
    """

    if copy_net:
        Net = NET().cuda()
        Net.load_state_dict(net.state_dict())
        Net.eval()
    else:
        Net = net

    class_correct = list(0 for _ in range(2))
    class_total = list(0 for _ in range(2))

    for (inputs, labels) in test_loader:
        inputs, labels = [Variable(input).cuda() for input in inputs], labels.cuda()
        outputs = Net(inputs)
        _, predicted = torch.max(outputs.data, 1)
        c = (predicted == labels).squeeze()
        for i in range(BATCH_SIZE):
            label = i
            try:
                class_correct[label] += c[i]
                class_total[label] += 1
            except IndexError:
                continue

    for i in range(2):
        print('Accuracy of %5s : %2d %%' % (
            i, 100 * class_correct[i] / class_total[i]))

    return [100 * class_correct[i] / class_total[i] for i in range(2)]


def save_model(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save(net.state_dict(), path)


def load_model(path):
    return net.load_state_dict(torch.load(path))


def test(net, copy_net=False):
    """
    :param net: the net to test on
    :param copy_net: boolean, whether to copy the net (if in the middle of training, you won't want to use the current net)
    """
    if copy_net:
        Net = NET().cuda()
        Net.load_state_dict(net.state_dict())
        Net.eval()
    else:
        Net = net

    correct = 0
    total = 0
    for (inputs, labels) in test_loader:
        inputs, labels = [Variable(input).cuda() for input in inputs], labels.cuda()
        outputs = Net(inputs)
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum()

    correct = 100 * correct / total
    print('Accuracy of the network on the test images: %d %%' % correct)
    return correct


def test_on_training(net, copy_net=False):
    if copy_net:
        Net = NET().cuda()
        Net.load_state_dict(net.state_dict())
        Net.eval()
    else:
        Net = net

    correct = 0
    total = 0
    for (inputs, labels) in train_test_loader:
        inputs, labels = [Variable(input).cuda() for input in inputs], labels.cuda()
        outputs = Net(inputs)
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum()

    correct = 100 * correct / total
    print('Accuracy of the network on the train images: %d %%' % correct)
    return correct

from pprint import pprint
# Train and test
def train(epoch):
    running_loss = 0.0
    for i, (true_inputs, true_labels) in enumerate(train_loader, 0):
        # wrap them in Variable
        inputs, labels = [Variable(input).cuda() for input in true_inputs], Variable(true_labels).cuda()

        # zero the parameter gradients
        optimizer.zero_grad()

        # forward + backward + optimize
        outputs = net(inputs)

        # Computer the loss
        loss = criterion(outputs, labels)

        # backpropagate and update optimizer learning rate
        loss.backward()
        optimizer.step()

        running_loss += loss.data[0]

        def print_loss():
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, int(i * len(true_inputs) * BATCH_SIZE / 2), len(train_loader) * BATCH_SIZE,
                       100. * i / len(train_loader), loss.data[0]))

            summary.add_scalar_value('train_loss', loss.data[0])

        def test_loss():
            summary.add_scalar_value('test_amount_correct', test(net, copy_net=True))
            summary.add_scalar_value('train_amount_correct', test_on_training(net, copy_net=True))


        def class_eval():
            values = class_evaluation(net, copy_net=True)
            #summary.add_scalar_dict(data={'test_noise': values[0], 'test_local': values[1], 'test_nonlocal': values[2]}, step=epoch)


        def write_model():
            path = f'./checkpoints/{NET.__name__}/model{epoch}.pt'
            save_model(path)

        if i % 2 == 0:
            print_loss()


        if (epoch % 3 == 0) and i == 0:
            test_loss()
            # class_eval()

        if (epoch % 10 == 0) and (i == 0):
            write_model()
            class_eval()

if __name__ == '__main__':
    for epoch in range(5000):
         train(epoch)
    #######################

    path = f'./checkpoints/{NET.__name__}/model40.pt'
    load_model(path)
    net.eval()

    test_on_training(net)
    class_evaluation(net)
    guess_labels(1)
    pass