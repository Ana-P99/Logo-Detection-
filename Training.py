#!/usr/bin/env python
# coding: utf-8

# In[6]:


from __future__ import print_function
import tensorflow as tf
import numpy as np
from six.moves import cPickle as pickle
from six.moves import range
import sys
import os


# In[7]:


import tensorflow.compat.v1 as tf
FLAGS = tf.app.flags.FLAGS


# In[8]:


def del_all_flags(FLAGS):
    flags_dict = FLAGS._flags()    
    keys_list = [keys for keys in flags_dict]    
    for keys in keys_list:
        FLAGS.__delattr__(keys)

del_all_flags(tf.flags.FLAGS)


# In[9]:


tf.app.flags.DEFINE_string(
    "train_dir", "flickr_logos_27_dataset",
    "Directory where to write event logs and checkpoint.")
tf.app.flags.DEFINE_float("max_steps", 5001, "Number of batches to run.")
tf.app.flags.DEFINE_float("image_width", 64, "A width of an input image.")
tf.app.flags.DEFINE_float("image_height", 32, "A height of an input image.")
tf.app.flags.DEFINE_float("num_classes", 27, "Number of logo classes.")
tf.app.flags.DEFINE_float("learning_rate", 0.0001, "Learning rate")
tf.app.flags.DEFINE_float("batch_size", 64, "A batch size")
tf.app.flags.DEFINE_float("num_channels", 3,
                            "A number of channels of an input image.")
tf.app.flags.DEFINE_float("patch_size", 5,
                            "A patch size of convolution filter")

PICKLE_FILENAME = 'deep_logo.pickle'


# In[10]:


def accuracy(predictions, labels):
    return (100 * np.sum(np.argmax(predictions, 1) == np.argmax(labels, 1)) /
            predictions.shape[0])


# In[11]:


def reformat(dataset, labels):
    dataset = dataset.reshape((-1, FLAGS.image_width, FLAGS.image_height,
                               FLAGS.num_channels)).astype(np.float32)
    labels = (
        np.arange(FLAGS.num_classes) == labels[:, None]).astype(np.float32)
    return dataset, labels


# In[12]:


def model(data, w_conv1, b_conv1, w_conv2, b_conv2, w_conv3, b_conv3, w_fc1,
          b_fc1, w_fc2, b_fc2):
    # First layer
    h_conv1 = tf.nn.relu(
        tf.nn.conv2d(data, w_conv1, [1, 1, 1, 1], padding='SAME') + b_conv1)
    h_pool1 = tf.nn.max_pool(
        h_conv1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')

    # Second layer
    h_conv2 = tf.nn.relu(
        tf.nn.conv2d(h_pool1, w_conv2, [1, 1, 1, 1], padding='SAME') + b_conv2)
    h_pool2 = tf.nn.max_pool(
        h_conv2, ksize=[1, 1, 2, 1], strides=[1, 1, 2, 1], padding='SAME')

    # Third layer
    h_conv3 = tf.nn.relu(
        tf.nn.conv2d(h_pool2, w_conv3, [1, 1, 1, 1], padding='SAME') + b_conv3)
    h_pool3 = tf.nn.max_pool(
        h_conv3, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')

    # Fully connected layer
    conv_layer_flat = tf.reshape(h_pool3, [-1, 16 * 4 * 128])
    h_fc1 = tf.nn.relu(tf.matmul(conv_layer_flat, w_fc1) + b_fc1)

    # Output layer
    out = tf.matmul(h_fc1, w_fc2) + b_fc2

    return out


# In[13]:


def read_data():
    with open(PICKLE_FILENAME, 'rb') as f:
        save = pickle.load(f)
        train_dataset = save['train_dataset']
        train_labels = save['train_labels']
        valid_dataset = save['valid_dataset']
        valid_labels = save['valid_labels']
        test_dataset = save['test_dataset']
        test_labels = save['test_labels']
        del save
        print('Training set', train_dataset.shape, train_labels.shape)
        print('Valid set', valid_dataset.shape, valid_labels.shape)
        print('Test set', test_dataset.shape, test_labels.shape)

    return [train_dataset, valid_dataset,
            test_dataset], [train_labels, valid_labels, test_labels]


# In[14]:


def main():
    if len(sys.argv) > 1:
        f = np.load(sys.argv[1])

        # f.files has unordered keys ['arr_8', 'arr_9', 'arr_6'...]
        # Sorting keys by value of numbers
        initial_weights = [
            f[n] for n in sorted(f.files, key=lambda s: int(s[4:]))
        ]
    else:
        initial_weights = None

    # read input data
    dataset, labels = read_data()

    train_dataset, train_labels = reformat(dataset[0], labels[0])
    valid_dataset, valid_labels = reformat(dataset[1], labels[1])
    test_dataset, test_labels = reformat(dataset[2], labels[2])
    print('Training set', train_dataset.shape, train_labels.shape)
    print('Valid set', valid_dataset.shape, valid_labels.shape)
    print('Test set', test_dataset.shape, test_labels.shape)

    # Training model
    graph = tf.Graph()
    with graph.as_default():
        # Variables
        w_conv1 = tf.Variable(
            tf.truncated_normal(
                [FLAGS.patch_size, FLAGS.patch_size, FLAGS.num_channels, 48],
                stddev=0.1))
        b_conv1 = tf.Variable(tf.constant(0.1, shape=[48]))

        w_conv2 = tf.Variable(
            tf.truncated_normal(
                [FLAGS.patch_size, FLAGS.patch_size, 48, 64], stddev=0.1))
        b_conv2 = tf.Variable(tf.constant(0.1, shape=[64]))

        w_conv3 = tf.Variable(
            tf.truncated_normal(
                [FLAGS.patch_size, FLAGS.patch_size, 64, 128], stddev=0.1))
        b_conv3 = tf.Variable(tf.constant(0.1, shape=[128]))

        w_fc1 = tf.Variable(
            tf.truncated_normal([16 * 4 * 128, 2048], stddev=0.1))
        b_fc1 = tf.Variable(tf.constant(0.1, shape=[2048]))

        w_fc2 = tf.Variable(tf.truncated_normal([2048, FLAGS.num_classes]))
        b_fc2 = tf.Variable(tf.constant(0.1, shape=[FLAGS.num_classes]))

        # Params
        params = [
            w_conv1, b_conv1, w_conv2, b_conv2, w_conv3, b_conv3, w_fc1, b_fc1,
            w_fc2, b_fc2
        ]

        # Initial weights
        if initial_weights is not None:
            assert len(params) == len(initial_weights)
            assign_ops = [w.assign(v) for w, v in zip(params, initial_weights)]

        # Input data
        tf_train_dataset = tf.placeholder(
            tf.float32,
            shape=(FLAGS.batch_size, FLAGS.image_width, FLAGS.image_height,
                   FLAGS.num_channels))
        tf_train_labels = tf.placeholder(
            tf.float32, shape=(FLAGS.batch_size, FLAGS.num_classes))
        tf_valid_dataset = tf.constant(valid_dataset)
        tf_test_dataset = tf.constant(test_dataset)

        # Training computation
        logits = model(tf_train_dataset, w_conv1, b_conv1, w_conv2, b_conv2,
                       w_conv3, b_conv3, w_fc1, b_fc1, w_fc2, b_fc2)
        with tf.name_scope('loss'):
            loss = tf.reduce_sum(
                tf.nn.softmax_cross_entropy_with_logits(
                    logits=logits, labels=tf_train_labels))
            tf.summary.scalar('loss', loss)
        optimizer = tf.train.AdamOptimizer(FLAGS.learning_rate).minimize(loss)

        # Predictions for the training, validation, and test data
        train_prediction = tf.nn.softmax(logits)
        valid_prediction = tf.nn.softmax(
            model(tf_valid_dataset, w_conv1, b_conv1, w_conv2, b_conv2,
                  w_conv3, b_conv3, w_fc1, b_fc1, w_fc2, b_fc2))
        test_prediction = tf.nn.softmax(
            model(tf_test_dataset, w_conv1, b_conv1, w_conv2, b_conv2, w_conv3,
                  b_conv3, w_fc1, b_fc1, w_fc2, b_fc2))
        # Merge all summaries
        merged = tf.summary.merge_all()
        train_writer = tf.summary.FileWriter(FLAGS.train_dir + '/train')

        # Add ops to save and restore all the variables
        saver = tf.train.Saver()

    # Do training
    with tf.Session(graph=graph) as session:
        tf.global_variables_initializer().run()
        if initial_weights is not None:
            session.run(assign_ops)
            print('initialized by pre-learned values')
        else:
            print('initialized')
        for step in range(FLAGS.max_steps):
            offset = (step * FLAGS.batch_size) % (
                train_labels.shape[0] - FLAGS.batch_size)
            batch_data = train_dataset[offset:(offset + FLAGS.batch_size
                                               ), :, :, :]
            batch_labels = train_labels[offset:(offset + FLAGS.batch_size), :]
            feed_dict = {
                tf_train_dataset: batch_data,
                tf_train_labels: batch_labels
            }
            try:
                _, l, predictions = session.run(
                    [optimizer, loss, train_prediction], feed_dict=feed_dict)
                if step % 50 == 0:
                    summary, _ = session.run(
                        [merged, optimizer], feed_dict=feed_dict)
                    train_writer.add_summary(summary, step)
                    print('Minibatch loss at step %d: %f' % (step, l))
                    print('Minibatch accuracy: %.1f%%' %
                          accuracy(predictions, batch_labels))
                    print('Validation accuracy: %.1f%%' %
                          accuracy(valid_prediction.eval(), valid_labels))
            except KeyboardInterrupt:
                last_weights = [p.eval() for p in params]
                np.savez("weights.npz", *last_weights)
                return last_weights

        print('Test accuracy: %.1f%%' % accuracy(test_prediction.eval(),
                                                 test_labels))

        # Save the variables to disk.
        save_dir = "models"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        save_path = os.path.join(save_dir, "deep_logo_model")
        saved = saver.save(session, save_path)
        print("Model saved in file: %s" % saved)


# In[ ]:




