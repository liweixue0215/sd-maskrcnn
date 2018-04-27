import os
import sys
import logging
import argparse
import configparser
from tqdm import tqdm
from ast import literal_eval
import matplotlib
matplotlib.use('agg')
from matplotlib import pyplot as plt

import cv2
import skimage.io
import numpy as np
import tensorflow as tf

from eval_coco import *
from eval_saurabh import *
from augmentation import augment_img

from pipeline_utils import *
from clutter import ClutterConfig
import model as modellib, visualize, utils
from real_dataset import RealImageDataset, prepare_real_image_test
from sim_dataset import SimImageDataset

"""
Pipeline Usage Notes:

Please edit "config.ini" to specify the task you wish to perform and the
necessary parameters for that task.

Run this file with the tag --config [config file name] (in this case,
config.ini).

You should include in your PYTHONPATH the locations of maskrcnn and clutter
folders.

Here is an example run command (GPU selection included):
CUDA_VISIBLE_DEVICES='0' PYTHONPATH='.:maskrcnn/:clutter/' python3 noise/pipeline.py --config noise/config.ini
"""


def augment_data(config):
    """
    Using provided image directory and output directory, perform data
    augmentation methods on each image and save the new copy to the
    output directory.
    """
    img_dir = config["img_dir"]
    out_dir = config["out_dir"]

    mkdir_if_missing(out_dir)

    print("Augmenting data in directory {}.\n".format(img_dir))
    num_imgs = int(config["num_imgs"])
    count = 0
    for img_file in tqdm(os.listdir(img_dir), total=num_imgs):
        if count == num_imgs:
            break
        if img_file.endswith(".png"):
            # read in image
            img_path = os.path.join(img_dir, img_file)
            # img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
            img = skimage.io.imread(img_path, as_grey=True)

            # return list of augmented images and save
            new_img = augment_img(img, config)
            out_path = os.path.join(out_dir, img_file)
            # cv2.imwrite(out_path, new_img)
            skimage.io.imsave(out_path, new_img)
        count += 1

    print("Augmentation complete; files saved in {}.\n".format(out_dir))


def train(config):
    # read information from config
    dataset_path = config["base_path"]
    mean_pixel = config["mean_pixel"]
    img_type = config["img_type"]

    # Load the datasets, configs.
    train_config = ClutterConfig(mean=mean_pixel)
    train_config.display()

    # Training dataset
    dataset_train = SimImageDataset(dataset_path)
    dataset_train.load('train')
    dataset_train.prepare()

    # Validation dataset
    dataset_val = SimImageDataset(dataset_path)
    dataset_val.load('test')
    dataset_val.prepare()

    # Create the model.
    model = get_model(config, train_config)

    # train and save weights to model_path
    model.train(dataset_train, dataset_val, learning_rate=train_config.LEARNING_RATE,
                epochs=100, layers='all')
    model_path = os.path.join(model_dir, "mask_rcnn_clutter.h5")
    model.keras_model.save_weights(model_path)


def benchmark(config):
    print("Benchmarking model.")
    # Create new directory for run outputs
    output_dir = config['output_dir'] # In what location should we put this new directory?
    run_name = config['run_name'] # What is it called
    run_dir = os.path.join(output_dir, run_name)
    mkdir_if_missing(run_dir)

    # Save config
    # TODO: actually do it
    model_path = config['model_path']
    test_dir = config['test_dir'] # directory of test images and segmasks

    inference_config, model, dataset_real = prepare_real_image_test(model_path, test_dir)

    ######## BENCHMARK JUST CREATES THE RUN DIRECTORY ########
    # code that actually produces outputs should be plug-and-play
    # depending on what kind of benchmark function we run.

    coco_benchmark(run_dir, inference_config, model, dataset_real)

    s_benchmark(run_dir, inference_config, model, dataset_real)


    print("Saved benchmarking output to {}.\n".format(run_dir))


def read_config():
    # setting up flag parsing
    conf_parser = argparse.ArgumentParser(description="Augment data in path folder with various noise filters and transformations")

    # required argument for config file
    conf_parser.add_argument("--config", action="store", required=True,
                               dest="conf_file", type=str, help="path to the configuration file")
    conf_args = conf_parser.parse_args()

    # read in config file information from proper section
    conf = configparser.ConfigParser()
    conf.read([conf_args.conf_file])
    task = conf.get("GENERAL", "task").upper()
    task = literal_eval(task)

    # create a dictionary of the proper arguments, including
    # the requested task
    conf_dict = dict(conf.items(task))

    # return a type-sensitive version of the dictionary;
    # prevents further need to cast from string to other types
    out = {}
    for key, value in conf_dict.items():
        out[key] = literal_eval(value)
    out["task"] = task
    return out


if __name__ == "__main__":
    # parse the provided configuration file
    config = read_config()

    task = config["task"]
    print('config["task"]', config['task'])
    if task == "AUGMENT":
        augment_data(config)

    if task == "TRAIN":
        train(config)

    if task == "BENCHMARK":
        benchmark(config)
