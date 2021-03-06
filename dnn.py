from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation
from keras.callbacks import EarlyStopping
from keras.optimizers import SGD, RMSprop, Adam
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
import keras
import numpy as np
import timeit
import os
import sys

class TimeHistory(keras.callbacks.Callback):
    def on_train_begin(self, logs={}):
        self.timehistory = []

    def on_epoch_end(self, batch, logs={}):
        print(timeit.default_timer())
        self.timehistory.append(timeit.default_timer())
        logs['time'] = timeit.default_timer()

class AUCHistory(keras.callbacks.Callback):
    def __init__(self, train_data, test_data):
        self.train_data = train_data
        self.test_data = test_data

    def on_epoch_end(self, epoch, logs={}):
        train_x, train_y = self.train_data
        train_y_score = self.model.predict_proba(train_x, verbose=0)
        test_x, test_y = self.test_data
        test_y_score = self.model.predict_proba(test_x, verbose=0)
        logs['auc'] = roc_auc_score(test_y, test_y_score) 
        print('train roc_auc %.3f, test roc_auc %.3f\n' % (roc_auc_score(train_y, train_y_score), roc_auc_score(test_y, test_y_score)))

def setup():
    for dirname in ['model','result']:
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

def versions():
    versions = (('Keras',keras.__version__),
            ('numpy', np.version.version),
            ('Python', sys.version))
    return versions

def show_version():
    for version in versions():
        print(' '.join(version))

def validation(taskname, data, layers, epochs, class_weight, batch_size, optimizer, lr, 
        activation, dropout, patience, count):
    X = data[:,:-1]
    y = data[:,-1]

    optimizer = globals()[optimizer](lr=lr)

    start_time = timeit.default_timer()

    skf = StratifiedKFold(n_splits=5, shuffle=True)

    for fold, (train, test) in enumerate(skf.split(X, y), 1):
        callbacks = []
        if patience > 0:
            earlystopping = EarlyStopping(monitor='val_loss', patience=patience)
            callbacks.append(earlystopping)
        if count == 0:
            break

        timehistory = TimeHistory()
        callbacks.append(timehistory)
        auchistory = AUCHistory((X[train], y[train]), (X[test], y[test]))
        callbacks.append(auchistory)

        model = Sequential()

        # hidden layers
        for i, layer in enumerate(layers, 1):
            input_dim = X.shape[1] if i == 1 else layers[i-1]
            model.add(Dense(layer, input_dim=input_dim, init='uniform', name='Hidden%d' % i))
            model.add(Activation(activation, name='%s%d' % (activation, i)))
            if dropout > 0:
                model.add(Dropout(dropout, name='Dropout%d' % i))

        # output layer
        model.add(Dense(1, init='uniform', name='Output'))
        model.add(Activation('sigmoid', name='sigmoid'))

        model.summary()

        model.compile(loss='binary_crossentropy', optimizer=optimizer, metrics=['accuracy'],
        #        context=['gpu0','gpu1'])
        )

        # fitting
        history = model.fit(X[train], y[train], nb_epoch=epochs, batch_size=batch_size, 
                shuffle=True, validation_data=(X[test], y[test]), verbose=1, class_weight=class_weight,
                callbacks=callbacks)


        np.savetxt('result/fold%2d_proba.txt' % fold, (
            model.predict_proba(X[test])[:,0],
            y[test],
            ))

        np.savetxt('result/fold%2d_auc.txt' % fold, (
            history.history['val_loss'],
            history.history['val_acc'],
            history.history['loss'],
            history.history['acc'],
            history.history['time'],
            history.history['auc'],
            ))

        count -= 1

    end_time = timeit.default_timer()

    print('ran for %.1fs' % ((end_time - start_time)))

if __name__ == '__main__':
    show_version()
