import React from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { useSelector } from 'react-redux';

export default function ProfileScreen() {
  const player = useSelector((state) => state.player);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Profile</Text>
      <View style={styles.section}>
        <Text style={styles.label}>Username</Text>
        <Text style={styles.value}>{player.username}</Text>
      </View>
      <View style={styles.section}>
        <Text style={styles.label}>Level</Text>
        <Text style={styles.value}>{player.level}</Text>
      </View>
      <View style={styles.section}>
        <Text style={styles.label}>Class</Text>
        <Text style={styles.value}>{player.jobClass}</Text>
      </View>
      <View style={styles.section}>
        <Text style={styles.label}>Experience</Text>
        <Text style={styles.value}>{player.experience}</Text>
      </View>
      <View style={styles.attributes}>
        <Text style={styles.subTitle}>Attributes</Text>
        <Text style={styles.attribute}>STR: {player.strength}</Text>
        <Text style={styles.attribute}>DEX: {player.dexterity}</Text>
        <Text style={styles.attribute}>INT: {player.intelligence}</Text>
        <Text style={styles.attribute}>WIS: {player.wisdom}</Text>
        <Text style={styles.attribute}>CON: {player.constitution}</Text>
        <Text style={styles.attribute}>CHA: {player.charisma}</Text>
      </View>
      <View style={styles.section}>
        <Text style={styles.label}>Current Region</Text>
        <Text style={styles.value}>{player.region}</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#0f0f1a',
    minHeight: '100%',
    padding: 20,
  },
  title: {
    color: '#ff6b35',
    fontSize: 28,
    marginBottom: 20,
    fontWeight: '700',
  },
  section: {
    marginBottom: 16,
  },
  label: {
    color: '#bbb',
    fontSize: 14,
    marginBottom: 4,
  },
  value: {
    color: '#fff',
    fontSize: 18,
  },
  subTitle: {
    color: '#ff6b35',
    fontSize: 18,
    marginBottom: 12,
    fontWeight: '700',
  },
  attributes: {
    backgroundColor: '#15182f',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
  },
  attribute: {
    color: '#fff',
    fontSize: 16,
    marginBottom: 8,
  },
});
