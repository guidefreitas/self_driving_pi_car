#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tensorflow as tf
import os
import numpy as np
import shutil
import argparse

from DataHolder import DataHolder
from Config import Config
from Trainer import Trainer
from DFN import DFN
from CNN import CNN
from util import reconstruct_from_record, accuracy_per_category
from util import int2command


def optmizers_search(mode,
                     records,
                     height,
                     width,
                     channels,
                     architecture,
                     activations,
                     conv_architecture,
                     kernel_sizes,
                     pool_kernel,
                     batch_size,
                     epochs,
                     num_steps,
                     save_step,
                     learning_rate,
                     conv):
    """
    Script to run optmizers search,
    the result is saved on the file optmizers_results.txt

    :param channels: image channels
    :type channels: int
    :param records: list of paths to tf_records
    :type records: none or list of str
    """
    OT = [tf.train.GradientDescentOptimizer,
          tf.train.AdadeltaOptimizer,
          tf.train.AdagradOptimizer,
          tf.train.AdamOptimizer,
          tf.train.FtrlOptimizer,
          tf.train.ProximalGradientDescentOptimizer,
          tf.train.ProximalAdagradOptimizer,
          tf.train.RMSPropOptimizer]

    OT_name = ["GradientDescentOptimizer",
               "AdadeltaOptimizer",
               "AdagradOptimizer",
               "AdamOptimizer",
               "FtrlOptimizer",
               "ProximalGradientDescentOptimizer",
               "ProximalAdagradOptimizer",
               "RMSPropOptimizer"]
    numeric_result = []
    results = []
    info = []
    if conv:
        net_name = "CNN"
    else:
        net_name = "DFN"

    header = "\nSearching optimizer for the {} model in the {} data\n".format(net_name, # noqa
                                                                              mode) # noqa
    print(header)

    for name, opt in zip(OT_name, OT):
        config = Config(height=height,
                        width=width,
                        channels=channels,
                        architecture=architecture,
                        activations=activations,
                        conv_architecture=conv_architecture,
                        kernel_sizes=kernel_sizes,
                        pool_kernel=pool_kernel,
                        batch_size=batch_size,
                        epochs=epochs,
                        num_steps=num_steps,
                        save_step=save_step,
                        learning_rate=learning_rate,
                        optimizer=opt)
        data = DataHolder(config,
                          records=records)
        print(name + ":\n")
        graph = tf.Graph()
        if conv:
            network = CNN(graph, config)
        else:
            network = DFN(graph, config)
        trainer = Trainer(graph, config, network, data)
        trainer.fit(verbose=True)
        valid_acc = trainer.get_valid_accuracy()
        numeric_result.append(valid_acc)
        name += ': valid_acc = {0:.6f} | '.format(valid_acc)
        test_images, test_labels, _ = reconstruct_from_record(data.get_test_tfrecord())  # noqa
        test_images = test_images.astype(np.float32) / 255
        test_pred = trainer.predict(test_images)
        acc_cat = accuracy_per_category(test_pred, test_labels, categories=3)
        for i, cat_result in enumerate(acc_cat):
            name += int2command[i] + ": = {0:.6f}, ".format(cat_result)
        results.append(name)
        if os.path.exists("checkpoints"):
            shutil.rmtree("checkpoints")
        info.append(config.get_status())

    best_result = max(list(zip(numeric_result, OT_name, info)))
    result_string = """In an experiment with different optmizers
    the best one is {0} with valid accuracy of {1}.
    \nThe training uses the following params:
    \n{2}\n""".format(best_result[1],
                      best_result[0],
                      best_result[2])
    file = open("optmizers_results.txt", "w")
    file.write(header)
    file.write("Results for different optmizers\n")
    for result in results:
        result += "\n"
        file.write(result)
    file.write("\n")
    file.write(result_string)
    file.close()


def main():
    """
    Main script to perform optmizer search.

    "mode" is the argument to choose which kind of data will be used:
        "pure": rgb image with no manipulation.
        "flip": flippped rgb image (a image with label "left" is
                flipped and transform in an image with label
                "right", and vice versa; to have a balanced data).
        "aug": flippped rgb image with new shadowed and blurred images.
        "bin": binary image, only one channel.
        "gray": grayscale image, only one channel.
        "green": image with only the green channel.
    """
    parser = argparse.ArgumentParser(description='Perform optmizer search')
    parser.add_argument("-m",
                        "--mode",
                        type=str,
                        default="pure",
                        help="mode for data: pure, flip, aug, bin, gray, green (default=pure)")  # noqa
    parser.add_argument('-a',
                        '--architecture',
                        type=int,
                        nargs='+',
                        help='sizes for hidden layers and output layer, should end with at least "3" !, (default=[3])',  # noqa
                        default=[3])
    parser.add_argument('-ac',
                        '--activations',
                        type=str,
                        nargs='+',
                        help='activations: relu, sigmoid, tanh (defaul=None)',
                        default=None)
    parser.add_argument("-he",
                        "--height",
                        type=int,
                        default=90,
                        help="image height (default=90)")
    parser.add_argument("-w",
                        "--width",
                        type=int,
                        default=160,
                        help="image width (default=160)")
    parser.add_argument("-lr",
                        "--learning_rate",
                        type=float,
                        default=0.02,
                        help="learning rate (default=0.02)")
    parser.add_argument('-conva',
                        '--conv_architecture',
                        type=int,
                        nargs='+',
                        help='filters for conv layers (default=[32, 64])',  # noqa
                        default=[32, 64])
    parser.add_argument('-k',
                        '--kernel_sizes',
                        type=int,
                        nargs='+',
                        help='kernel sizes for conv layers (default=None - 5 for every layer)',  # noqa
                        default=None)
    parser.add_argument('-p',
                        '--pool_kernel',
                        type=int,
                        nargs='+',
                        help='kernel sizes for pooling layers (default=None - 2 for every layer)',  # noqa
                        default=None)
    parser.add_argument("-b",
                        "--batch_size",
                        type=int,
                        default=32,
                        help="batch size (default=32)")
    parser.add_argument("-e",
                        "--epochs",
                        type=int,
                        default=5,
                        help="epochs for training (default=5)")
    parser.add_argument("-ns",
                        "--num_steps",
                        type=int,
                        default=1000,
                        help="number of steps for each epoch (default=1000)")
    parser.add_argument("-ss",
                        "--save_step",
                        type=int,
                        default=100,
                        help="number of steps to save variables (default=100)")
    parser.add_argument("-conv",
                        "--conv",
                        action="store_true",
                        default=False,
                        help="Use convolutional network (default=False)")
    args = parser.parse_args()
    if args.mode == "bin" or args.mode == "gray" or args.mode == "green":
        channels = 1
    else:
        channels = 3
    records = ["_train.tfrecords", "_valid.tfrecords", "_test.tfrecords"]
    new_records = []
    for record in records:
        record = args.mode + record
        new_records.append(record)

    activations_dict = {"relu": tf.nn.relu,
                        "sigmoid": tf.nn.sigmoid,
                        "tanh": tf.nn.tanh}
    if args.activations is not None:
        activations = [activations_dict[act] for act in args.activations]
    else:
        activations = args.activations
    optmizers_search(mode=args.mode,
                     records=new_records,
                     height=args.height,
                     width=args.width,
                     channels=channels,
                     architecture=args.architecture,
                     activations=activations,
                     conv_architecture=args.conv_architecture,
                     kernel_sizes=args.kernel_sizes,
                     pool_kernel=args.pool_kernel,
                     batch_size=args.batch_size,
                     epochs=args.epochs,
                     learning_rate=args.learning_rate,
                     num_steps=args.num_steps,
                     save_step=args.save_step,
                     conv=args.conv)


if __name__ == "__main__":
    main()
