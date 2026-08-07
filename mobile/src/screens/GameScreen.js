import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import api from '../services/api';
import { setPlayer } from '../store/playerSlice';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function GameScreen() {
  const dispatch = useDispatch();
  const player = useSelector((state) => state.player);
  const [loading, setLoading] = useState(true);

  const loadProfile = async () => {
    try {
      setLoading(true);
      const response = await api.get('/player/profile');
      const data = response.data;
      dispatch(
        setPlayer({
          id: data.id,
          username: data.username,
          level: data.level,
          experience: data.experience,
          species: data.species,
          speciesVariant: data.species_variant,
          jobClass: data.job_class,
          jobLevel: data.job_level,
          mainClass: data.main_class,
          subClass: data.sub_class,
          strength: data.stats.strength,
          dexterity: data.stats.dexterity,
          intelligence: data.stats.intelligence,
          wisdom: data.stats.wisdom,
          constitution: data.stats.constitution,
          charisma: data.stats.charisma,
          luck: data.stats.luck,
          current_hp: data.current_hp,
          max_hp: data.max_hp,
          current_mana: data.current_mana,
          max_mana: data.max_mana,
          current_stamina: data.current_stamina,
          max_stamina: data.max_stamina,
          hunger: data.hunger,
          currency: data.currency,
          guilds: data.guilds,
          skills: data.skills,
        }),
      );
    } catch (error) {
      console.error(error);
      Alert.alert('Error', 'Failed to load profile.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#ff6b35" />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Welcome back, {player.username}</Text>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Level</Text>
        <Text style={styles.cardValue}>{player.level}</Text>
      </View>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>HP / Mana / Stamina</Text>
        <Text style={styles.cardValue}>{player.current_hp} / {player.current_mana} / {player.current_stamina}</Text>
      </View>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Region</Text>
        <Text style={styles.cardValue}>{player.region}</Text>
      </View>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Currency</Text>
        <Text style={styles.cardValue}>Kupdun: {player.currency.kupdun} · Zirdun: {player.currency.zirdun} · Guldun: {player.currency.guldun}</Text>
      </View>
      <TouchableOpacity style={styles.refreshButton} onPress={loadProfile}>
        <Text style={styles.refreshText}>Refresh Profile</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: '#0f0f1a',
    minHeight: '100%',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0f0f1a',
  },
  title: {
    color: '#ff6b35',
    fontSize: 28,
    marginBottom: 20,
    fontWeight: '700',
  },
  card: {
    backgroundColor: '#15182f',
    padding: 16,
    borderRadius: 16,
    marginBottom: 16,
  },
  cardTitle: {
    color: '#bbb',
    marginBottom: 8,
    fontSize: 14,
  },
  cardValue: {
    color: '#fff',
    fontSize: 18,
  },
  refreshButton: {
    marginTop: 12,
    backgroundColor: '#ff6b35',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  refreshText: {
    color: '#fff',
    fontWeight: '700',
  },
});
