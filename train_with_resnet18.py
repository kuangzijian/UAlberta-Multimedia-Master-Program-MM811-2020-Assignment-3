import pandas as pd
import numpy as np
from tqdm import tqdm
from skimage.io import imread
from skimage.transform import resize
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import torch
import torch.optim as optim
from torch.nn import CrossEntropyLoss, Sequential
from torchvision import models
import torch.nn as nn

# loading dataset
train = pd.read_csv('dataset/emergency_train.csv')
train.head()

# loading training images
train_img = []
for img_name in tqdm(train['image_names']):
    # defining the image path
    image_path = 'dataset/images/' + img_name
    # reading the image
    img = imread(image_path)
    # normalizing the pixel values
    img = img/255
    # resizing the image to (224,224,3)
    img = resize(img, output_shape=(224, 224, 3), mode='constant', anti_aliasing=True)
    # converting the type of pixel to float 32
    img = img.astype('float32')
    # appending the image into the list
    train_img.append(img)

# converting the list to numpy array
train_x = np.array(train_img)
train_x.shape
print(train_x.shape)

# defining the target
train_y = train['emergency_or_not'].values

# create validation set
train_x, val_x, train_y, val_y = train_test_split(train_x, train_y, test_size=0.1, random_state=13, stratify=train_y)
print((train_x.shape, train_y.shape), (val_x.shape, val_y.shape))


# converting training images into torch format
train_x = train_x.reshape(1481, 3, 224, 224)
train_x = torch.from_numpy(train_x)

# converting the target into torch format
train_y = train_y.astype(int)
train_y = torch.from_numpy(train_y)

# shape of training data
print(train_x.shape, train_y.shape)

# converting validation images into torch format
val_x = val_x.reshape(165, 3, 224, 224)
val_x = torch.from_numpy(val_x)

# converting the target into torch format
val_y = val_y.astype(int)
val_y = torch.from_numpy(val_y)

# shape of validation data
print(val_x.shape, val_y.shape)

# loading the pre-trained ResNet18 model
model = models.resnet18(pretrained=True)

# Freeze model weights
for param in model.parameters():
    param.requires_grad = False

# checking if GPU is available
if torch.cuda.is_available():
    model = model.cuda()

# Add fine-tuning FC layers
model.fc = Sequential(
    nn.Linear(512, 1000),
    nn.ReLU(True),
    nn.Dropout(),
    nn.Linear(1000, 4096),
    nn.ReLU(True),
    nn.Dropout(),
    nn.Linear(4096, 2),
    nn.LogSoftmax(dim=1))

model.fc = model.fc.cuda()
for param in model.fc.parameters():
    param.requires_grad = True

# Check how does our new model look like
print(model)

# batch_size
batch_size = 128

# specify loss function (categorical cross-entropy)
criterion = CrossEntropyLoss()

# specify optimizer (stochastic gradient descent) and learning rate
optimizer = optim.Adam(model.fc.parameters(), lr=0.0005)

batch_size = 128
n_epochs = 30

for epoch in tqdm(range(1, n_epochs + 1)):
    # keep track of training and validation loss
    train_loss = 0.0
    permutation = torch.randperm(train_x.size()[0])
    training_loss = []
    for i in range(0, train_x.size()[0], batch_size):

        indices = permutation[i:i + batch_size]
        batch_x, batch_y = train_x[indices], train_y[indices]

        if torch.cuda.is_available():
            batch_x, batch_y = batch_x.cuda(), batch_y.cuda()

        optimizer.zero_grad()
        outputs = model(batch_x.cuda())
        loss = criterion(outputs, batch_y.long())

        training_loss.append(loss.item())
        loss.backward()
        optimizer.step()

    training_loss = np.average(training_loss)
    print('epoch: \t', epoch, '\t training loss: \t', training_loss)

# prediction for training set
prediction = []
target = []
permutation = torch.randperm(train_x.size()[0])
for i in tqdm(range(0, train_x.size()[0], batch_size)):
    indices = permutation[i:i + batch_size]
    batch_x, batch_y = train_x[indices], train_y[indices]

    if torch.cuda.is_available():
        batch_x, batch_y = batch_x.cuda(), batch_y.cuda()

    with torch.no_grad():
        output = model(batch_x.cuda())

    prob = list(output.cpu().numpy())
    predictions = np.argmax(prob, axis=1)
    prediction.append(predictions)
    target.append(batch_y)

# training accuracy
accuracy = []
for i in range(len(prediction)):
    accuracy.append(accuracy_score(target[i].cpu(), prediction[i]))

print('training accuracy: \t', np.average(accuracy))

# prediction for validation set
prediction_val = []
target_val = []
permutation = torch.randperm(val_x.size()[0])
for i in tqdm(range(0, val_x.size()[0], batch_size)):
    indices = permutation[i:i + batch_size]
    batch_x, batch_y = val_x[indices], val_y[indices]

    if torch.cuda.is_available():
        batch_x, batch_y = batch_x.cuda(), batch_y.cuda()

    with torch.no_grad():
        output = model(batch_x.cuda())

    prob = list(output.cpu().numpy())
    predictions = np.argmax(prob, axis=1)
    prediction_val.append(predictions)
    target_val.append(batch_y)

# validation accuracy
accuracy_val = []
for i in range(len(prediction_val)):
    accuracy_val.append(accuracy_score(target_val[i].cpu(), prediction_val[i]))

print('validation accuracy: \t', np.average(accuracy_val))
