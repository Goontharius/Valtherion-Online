import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import api from '../services/api';
import WebSocketService from '../services/websocket';
import { setParty, clearParty, joinParty } from '../store/partySlice';
import { joinParty as playerJoinParty, leaveParty as playerLeaveParty } from '../store/playerSlice';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function PartyScreen() {
  const dispatch = useDispatch();
  const player = useSelector((state) => state.player);
  const party = useSelector((state) => state.party);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [partyName, setPartyName] = useState('');
  const [inviteName, setInviteName] = useState('');
  const [busy, setBusy] = useState(false);

  const loadParty = async () => {
    try {
      setLoading(true);
      const response = await api.get('/party/me');
      dispatch(setParty(response.data));
      dispatch(playerJoinParty(response.data.id));
    } catch (error) {
      if (error.response?.status === 404) {
        dispatch(clearParty());
        dispatch(playerLeaveParty());
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadParty();

    const connectWebSocket = async () => {
      const token = await AsyncStorage.getItem('auth_token');
      if (token) {
        WebSocketService.connect(token);
        WebSocketService.on('message', handleIncomingMessage);
        WebSocketService.on('party_member_joined', handlePartyUpdate);
      }
    };

    connectWebSocket();

    return () => {
      WebSocketService.off('message', handleIncomingMessage);
      WebSocketService.off('party_member_joined', handlePartyUpdate);
    };
  }, []);

  const handleIncomingMessage = (data) => {
    if (data?.type === 'party_member_joined') {
      dispatch(setParty({ ...party, members: data.members, member_details: data.member_details || party.member_details }));
    }
  };

  const handlePartyUpdate = (data) => {
    loadParty();
  };

  const runAction = async (label, request) => {
    if (busy) return;
    setBusy(true);
    try {
      await request();
      await loadParty();
      setInviteName('');
    } catch (error) {
      const detail = error.response?.data?.detail || error.message;
      Alert.alert(label, typeof detail === 'string' ? detail : 'Request failed.');
    } finally {
      setBusy(false);
    }
  };

  const createParty = () =>
    runAction('Create Party Failed', () =>
      api.post('/party/create', { name: partyName, emblem: {} }),
    );

  const invitePlayer = () => {
    if (!inviteName.trim()) return;
    runAction('Invite Failed', () => api.post(`/party/invite/${inviteName.trim()}`));
  };

  const kickPlayer = (id) =>
    runAction('Kick Failed', () => api.post(`/party/kick/${id}`));

  const leaveParty = () =>
    runAction('Leave Failed', () => api.post('/party/leave'));

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#ff6b35" />
      </View>
    );
  }

  const isLeader = party.leader_id === player.id;

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Party</Text>

      {!party.id ? (
        <View>
          <View style={styles.card}>
            <Text style={styles.cardText}>You are not in a party.</Text>
            <TouchableOpacity
              style={styles.button}
              onPress={() => setShowCreate(!showCreate)}
            >
              <Text style={styles.buttonText}>
                {showCreate ? 'Cancel' : 'Create Party'}
              </Text>
            </TouchableOpacity>
          </View>

          {showCreate && (
            <View style={styles.card}>
              <TextInput
                style={styles.input}
                placeholder="Party name"
                placeholderTextColor="#888"
                value={partyName}
                onChangeText={setPartyName}
              />
              <TouchableOpacity style={styles.button} onPress={createParty} disabled={busy || !partyName.trim()}>
                <Text style={styles.buttonText}>Create</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      ) : (
        <View>
          <View style={styles.card}>
            <Text style={styles.partyName}>{party.name}</Text>
            <Text style={styles.partyMeta}>
              {party.member_count || (party.members || []).length} / {party.max_members} members
              {isLeader ? ' · You are the leader' : ''}
            </Text>
            <Text style={styles.partyMeta}>
              Loot: {party.loot_mode} · XP share: {party.experience_share ? 'On' : 'Off'}
            </Text>
          </View>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>Members</Text>
            {(party.member_details || []).map((member) => (
              <View key={member.id} style={styles.memberRow}>
                <View style={styles.memberInfo}>
                  <Text style={styles.memberName}>
                    {member.username}
                    {member.id === party.leader_id ? ' 👑' : ''}
                    {member.id === player.id ? ' (you)' : ''}
                  </Text>
                  <Text style={styles.memberMeta}>
                    Level {member.level} {member.job_class}
                  </Text>
                </View>
                {isLeader && member.id !== player.id && (
                  <TouchableOpacity
                    style={styles.kickButton}
                    onPress={() => kickPlayer(member.id)}
                    disabled={busy}
                  >
                    <Text style={styles.kickText}>Kick</Text>
                  </TouchableOpacity>
                )}
              </View>
            ))}
          </View>

          {isLeader && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Invite Player</Text>
              <View style={styles.inviteRow}>
                <TextInput
                  style={[styles.input, styles.inviteInput]}
                  placeholder="Username"
                  placeholderTextColor="#888"
                  value={inviteName}
                  onChangeText={setInviteName}
                  autoCapitalize="none"
                />
                <TouchableOpacity
                  style={styles.button}
                  onPress={invitePlayer}
                  disabled={busy || !inviteName.trim()}
                >
                  <Text style={styles.buttonText}>Invite</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}

          <TouchableOpacity style={styles.leaveButton} onPress={leaveParty} disabled={busy}>
            <Text style={styles.leaveText}>Leave Party</Text>
          </TouchableOpacity>
        </View>
      )}

      <TouchableOpacity style={styles.refreshButton} onPress={loadParty}>
        <Text style={styles.refreshText}>Refresh</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#0f0f1a',
    minHeight: '100%',
    padding: 20,
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
    color: '#ff6b35',
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 12,
  },
  cardText: {
    color: '#ccc',
    fontSize: 16,
    marginBottom: 16,
  },
  partyName: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 6,
  },
  partyMeta: {
    color: '#bbb',
    fontSize: 14,
    marginTop: 4,
  },
  memberRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomColor: '#252b47',
    borderBottomWidth: 1,
  },
  memberInfo: {
    flex: 1,
  },
  memberName: {
    color: '#fff',
    fontSize: 16,
  },
  memberMeta: {
    color: '#888',
    fontSize: 13,
    marginTop: 2,
  },
  kickButton: {
    backgroundColor: '#5c2233',
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  kickText: {
    color: '#ff6b6b',
    fontWeight: '700',
  },
  inviteRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  input: {
    flex: 1,
    height: 46,
    backgroundColor: '#1f1f3b',
    borderRadius: 12,
    paddingHorizontal: 12,
    color: '#fff',
  },
  inviteInput: {
    marginRight: 8,
  },
  button: {
    backgroundColor: '#ff6b35',
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 10,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '700',
  },
  leaveButton: {
    marginTop: 4,
    backgroundColor: '#5c2233',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  leaveText: {
    color: '#ff6b6b',
    fontWeight: '700',
  },
  refreshButton: {
    marginTop: 16,
    backgroundColor: '#252b47',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  refreshText: {
    color: '#ccc',
    fontWeight: '700',
  },
});
