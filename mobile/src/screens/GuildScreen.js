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
import { setPlayer } from '../store/playerSlice';

const GUILD_TYPES = ['Adventurers', 'Merchants', 'Assassins', 'Dark', 'Order'];

export default function GuildScreen() {
  const dispatch = useDispatch();
  const player = useSelector((state) => state.player);
  const [loading, setLoading] = useState(true);
  const [guild, setGuild] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showBrowse, setShowBrowse] = useState(false);
  const [guildList, setGuildList] = useState([]);
  const [missions, setMissions] = useState([]);
  const [guildName, setGuildName] = useState('');
  const [guildType, setGuildType] = useState('Adventurers');
  const [busy, setBusy] = useState(false);

  const loadMyGuild = async () => {
    try {
      setLoading(true);
      const response = await api.get('/guild/my');
      setGuild(response.data);
      try {
        const missionsResponse = await api.get(`/guild/missions/${response.data.type}`);
        setMissions(missionsResponse.data);
      } catch (err) {
        setMissions([]);
      }
    } catch (error) {
      if (error.response?.status === 404) {
        setGuild(null);
        setMissions([]);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadGuilds = async () => {
    try {
      const response = await api.get('/guild/');
      setGuildList(response.data);
    } catch (error) {
      Alert.alert('Error', 'Failed to load guild list.');
    }
  };

  useEffect(() => {
    loadMyGuild();
  }, []);

  const runAction = async (label, request) => {
    if (busy) return;
    setBusy(true);
    try {
      await request();
      await loadMyGuild();
      setShowCreate(false);
      setGuildName('');
    } catch (error) {
      const detail = error.response?.data?.detail || error.message;
      Alert.alert(label, typeof detail === 'string' ? detail : 'Request failed.');
    } finally {
      setBusy(false);
    }
  };

  const createGuild = () =>
    runAction('Create Guild Failed', () =>
      api.post('/guild/create', {
        name: guildName,
        guild_type: guildType,
        tribute: { kupdun: 5000 },
        emblem: {},
      }),
    );

  const joinGuild = (id, name) =>
    runAction('Join Failed', () => api.post(`/guild/join/${id}`));

  const leaveGuild = () =>
    runAction('Leave Failed', () => api.post('/guild/leave'));

  const refreshProfile = async () => {
    try {
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
          current_hp: data.vitals.current_hp,
          max_hp: data.vitals.max_hp,
          current_mana: data.vitals.current_mana,
          max_mana: data.vitals.max_mana,
          current_stamina: data.vitals.current_stamina,
          max_stamina: data.vitals.max_stamina,
          hunger: data.vitals.hunger,
          currency: data.currency,
          guilds: data.guilds,
          skills: data.skills,
        }),
      );
    } catch (error) {
      console.error(error);
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#ff6b35" />
      </View>
    );
  }

  const isLeader = guild && guild.leader_id === player.id;

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Guild</Text>

      {!guild ? (
        <View>
          <View style={styles.card}>
            <Text style={styles.cardText}>
              You are not in a guild. Join an existing guild or found your own (Level 25 + 5000 Kupdun required).
            </Text>
            <TouchableOpacity style={styles.button} onPress={() => setShowCreate(!showCreate)}>
              <Text style={styles.buttonText}>{showCreate ? 'Cancel' : 'Create Guild'}</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.buttonSecondary} onPress={() => {
              setShowBrowse(!showBrowse);
              if (!showBrowse) loadGuilds();
            }}>
              <Text style={styles.buttonSecondaryText}>{showBrowse ? 'Hide Guilds' : 'Browse Guilds'}</Text>
            </TouchableOpacity>
          </View>

          {showCreate && (
            <View style={styles.card}>
              <TextInput
                style={styles.input}
                placeholder="Guild name"
                placeholderTextColor="#888"
                value={guildName}
                onChangeText={setGuildName}
              />
              <Text style={styles.fieldLabel}>Guild Type</Text>
              <View style={styles.typeRow}>
                {GUILD_TYPES.map((type) => (
                  <TouchableOpacity
                    key={type}
                    style={[styles.typeChip, guildType === type && styles.typeChipActive]}
                    onPress={() => setGuildType(type)}
                  >
                    <Text style={[styles.typeChipText, guildType === type && styles.typeChipTextActive]}>
                      {type}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
              <TouchableOpacity
                style={styles.button}
                onPress={createGuild}
                disabled={busy || !guildName.trim()}
              >
                <Text style={styles.buttonText}>Create ({guildType})</Text>
              </TouchableOpacity>
            </View>
          )}

          {showBrowse && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Guilds of Valtherion</Text>
              {guildList.length === 0 ? (
                <Text style={styles.emptyText}>No guilds found yet.</Text>
              ) : (
                guildList.map((g) => (
                  <View key={g.id} style={styles.guildRow}>
                    <View style={styles.guildInfo}>
                      <Text style={styles.guildName}>{g.name}</Text>
                      <Text style={styles.guildMeta}>
                        {g.type} · Level {g.level} · {g.member_count}/50 members
                      </Text>
                      <Text style={styles.guildMeta}>Hall: {g.hall_region || 'Unknown'}</Text>
                    </View>
                    <TouchableOpacity style={styles.buttonSmall} onPress={() => joinGuild(g.id, g.name)} disabled={busy}>
                      <Text style={styles.buttonText}>Join</Text>
                    </TouchableOpacity>
                  </View>
                ))
              )}
            </View>
          )}
        </View>
      ) : (
        <View>
          <View style={styles.card}>
            <Text style={styles.guildName}>{guild.name}</Text>
            <Text style={styles.guildMeta}>
              {guild.type} Guild · Level {guild.level} · Likeness {guild.likeness}
            </Text>
            <Text style={styles.guildMeta}>
              {guild.member_count}/{guild.member_capacity} members
              {isLeader ? ' · You are the leader' : ''}
            </Text>
            <Text style={styles.guildMeta}>
              Treasury: {guild.treasury.kupdun} K · {guild.treasury.zirdun} Z · {guild.treasury.guldun} G
            </Text>
            <Text style={styles.guildMeta}>Guild Hall: {guild.hall_region || 'Unknown'}</Text>
          </View>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>Members</Text>
            {(guild.member_details || []).map((member) => (
              <View key={member.id} style={styles.memberRow}>
                <Text style={styles.memberName}>
                  {member.username}
                  {member.id === guild.leader_id ? ' 👑' : ''}
                  {member.id === player.id ? ' (you)' : ''}
                </Text>
                <Text style={styles.memberMeta}>
                  Level {member.level} {member.job_class}
                </Text>
              </View>
            ))}
          </View>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>Guild Missions</Text>
            {missions.length === 0 ? (
              <Text style={styles.emptyText}>No missions available for this guild type.</Text>
            ) : (
              missions.map((mission) => (
                <View key={mission.id} style={styles.missionRow}>
                  <View style={styles.missionInfo}>
                    <Text style={styles.missionName}>{mission.name}</Text>
                    <Text style={styles.missionDesc}>{mission.description}</Text>
                  </View>
                  <View style={styles.missionMeta}>
                    <Text style={styles.missionReward}>{mission.reward} XP</Text>
                    <Text style={styles.missionDifficulty}>{mission.difficulty}</Text>
                  </View>
                </View>
              ))
            )}
          </View>

          <TouchableOpacity style={styles.leaveButton} onPress={leaveGuild} disabled={busy}>
            <Text style={styles.leaveText}>Leave Guild</Text>
          </TouchableOpacity>
        </View>
      )}

      <TouchableOpacity style={styles.refreshButton} onPress={() => { loadMyGuild(); refreshProfile(); }}>
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
    fontSize: 15,
    marginBottom: 16,
    lineHeight: 22,
  },
  emptyText: {
    color: '#888',
    fontSize: 14,
  },
  guildName: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 6,
  },
  guildMeta: {
    color: '#bbb',
    fontSize: 14,
    marginTop: 4,
  },
  guildRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomColor: '#252b47',
    borderBottomWidth: 1,
  },
  guildInfo: {
    flex: 1,
    marginRight: 8,
  },
  memberRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomColor: '#252b47',
    borderBottomWidth: 1,
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
  missionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomColor: '#252b47',
    borderBottomWidth: 1,
  },
  missionInfo: {
    flex: 1,
    marginRight: 8,
  },
  missionName: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
  },
  missionDesc: {
    color: '#aaa',
    fontSize: 13,
    marginTop: 2,
  },
  missionMeta: {
    alignItems: 'flex-end',
  },
  missionReward: {
    color: '#ff6b35',
    fontSize: 13,
    fontWeight: '700',
  },
  missionDifficulty: {
    color: '#888',
    fontSize: 12,
    marginTop: 2,
    textTransform: 'capitalize',
  },
  input: {
    height: 46,
    backgroundColor: '#1f1f3b',
    borderRadius: 12,
    paddingHorizontal: 12,
    color: '#fff',
    marginBottom: 12,
  },
  fieldLabel: {
    color: '#bbb',
    fontSize: 14,
    marginBottom: 8,
  },
  typeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 12,
  },
  typeChip: {
    backgroundColor: '#1f1f3b',
    borderRadius: 10,
    paddingVertical: 8,
    paddingHorizontal: 12,
    marginRight: 8,
    marginBottom: 8,
  },
  typeChipActive: {
    backgroundColor: '#ff6b35',
  },
  typeChipText: {
    color: '#ccc',
    fontSize: 13,
  },
  typeChipTextActive: {
    color: '#fff',
    fontWeight: '700',
  },
  button: {
    backgroundColor: '#ff6b35',
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '700',
  },
  buttonSecondary: {
    backgroundColor: '#1f1f3b',
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonSecondaryText: {
    color: '#ccc',
    fontWeight: '700',
  },
  buttonSmall: {
    backgroundColor: '#ff6b35',
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 14,
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
