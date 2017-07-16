#! /usr/bin/python3
# -*- coding: utf-8 -*-
import time;

def log(level, text):
	time.tzset()
	localtime = time.strftime('%d %b %Y %H:%M:%S %Z', time.localtime(time.time()) )
	print("[" + level + "|" + localtime + "] " + text)

def log(text):
	log("INFO", text)