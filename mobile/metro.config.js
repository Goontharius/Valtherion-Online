const path = require('path');
const exclusionList = require('metro-config/src/defaults/exclusionList');
const {getDefaultConfig, mergeConfig} = require('@react-native/metro-config');

const config = {
  resolver: {
    blockList: exclusionList([
      new RegExp(`${path.resolve(__dirname, 'ios/Pods').replace(/[/\\]/g, '[/\\\\]')}.*`),
      new RegExp(`${path.resolve(__dirname, 'ios/build').replace(/[/\\]/g, '[/\\\\]')}.*`),
    ]),
  },
};

module.exports = mergeConfig(getDefaultConfig(__dirname), config);
