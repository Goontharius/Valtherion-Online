import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Switch,
  Alert,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { logout } from '../store/playerSlice';
import WebSocketService from '../services/websocket';

export default function SettingsScreen() {
  const dispatch = useDispatch();
  const player = useSelector((state) => state.player);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [musicEnabled, setMusicEnabled] = useState(true);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [busy, setBusy] = useState(false);

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: async () => {
            setBusy(true);
            try {
              WebSocketService.disconnect();
              await AsyncStorage.removeItem('auth_token');
              await AsyncStorage.removeItem('refresh_token');
              dispatch(logout());
            } catch (error) {
              Alert.alert('Error', 'Failed to logout. Please restart the app.');
            } finally {
              setBusy(false);
            }
          },
        },
      ],
      { cancelable: true },
    );
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Settings</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Account</Text>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Username</Text>
          <Text style={styles.infoValue}>{player.username}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Level</Text>
          <Text style={styles.infoValue}>{player.level}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Class</Text>
          <Text style={styles.infoValue}>{player.jobClass}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Species</Text>
          <Text style={styles.infoValue}>
            {player.species}
            {player.speciesVariant && player.speciesVariant !== 'Base'
              ? ` (${player.speciesVariant})`
              : ''}
          </Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Region</Text>
          <Text style={styles.infoValue}>{player.region}</Text>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Audio</Text>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Sound Effects</Text>
          <Switch
            trackColor={{ false: '#444', true: '#ff6b35' }}
            thumbColor={soundEnabled ? '#fff' : '#aaa'}
            value={soundEnabled}
            onValueChange={setSoundEnabled}
          />
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Music</Text>
          <Switch
            trackColor={{ false: '#444', true: '#ff6b35' }}
            thumbColor={musicEnabled ? '#fff' : '#aaa'}
            value={musicEnabled}
            onValueChange={setMusicEnabled}
          />
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Notifications</Text>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Push Notifications</Text>
          <Switch
            trackColor={{ false: '#444', true: '#ff6b35' }}
            thumbColor={notificationsEnabled ? '#fff' : '#aaa'}
            value={notificationsEnabled}
            onValueChange={setNotificationsEnabled}
          />
        </View>
      </View>

      <TouchableOpacity
        style={styles.logoutButton}
        onPress={handleLogout}
        disabled={busy}
      >
        <Text style={styles.logoutText}>
          {busy ? 'Logging out...' : 'Logout'}
        </Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#0f0f1a',
    minHeight: '100%',
    padding: 20,
    paddingBottom: 40,
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
    color: '#ff6b35',
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 12,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomColor: '#252b47',
    borderBottomWidth: 1,
  },
  infoLabel: {
    color: '#bbb',
    fontSize: 14,
  },
  infoValue: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
  },
  settingLabel: {
    color: '#ddd',
    fontSize: 15,
  },
  logoutButton: {
    marginTop: 24,
    backgroundColor: '#5c2233',
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
  },
  logoutText: {
    color: '#ff6b6b',
    fontWeight: '700',
    fontSize: 16,
  },
});
