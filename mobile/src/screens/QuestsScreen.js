import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useDispatch } from 'react-redux';
import api from '../services/api';
import { addQuest, completeQuest, updateStats } from '../store/playerSlice';

const TABS = ['Available', 'Active', 'Completed'];

export default function QuestsScreen() {
  const dispatch = useDispatch();
  const [tab, setTab] = useState('Available');
  const [loading, setLoading] = useState(true);
  const [available, setAvailable] = useState([]);
  const [active, setActive] = useState([]);
  const [completed, setCompleted] = useState([]);
  const [busy, setBusy] = useState(false);

  const loadQuests = async () => {
    try {
      setLoading(true);
      const [availRes, activeRes, compRes] = await Promise.all([
        api.get('/quests/available'),
        api.get('/quests/active'),
        api.get('/quests/completed'),
      ]);
      setAvailable(availRes.data || []);
      setActive((activeRes.data?.active_quests) || []);
      setCompleted((compRes.data?.completed_quests) || []);
    } catch (error) {
      Alert.alert('Error', 'Failed to load quests.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQuests();
  }, []);

  const runAction = async (label, request) => {
    if (busy) return;
    setBusy(true);
    try {
      const response = await request();
      if (response.data?.experience !== undefined) {
        dispatch(
          updateStats({
            experience: response.data.experience,
          }),
        );
      }
      await loadQuests();
      return response;
    } catch (error) {
      const detail = error.response?.data?.detail || error.message;
      Alert.alert(label, typeof detail === 'string' ? detail : 'Request failed.');
    } finally {
      setBusy(false);
    }
  };

  const acceptQuest = (questId) =>
    runAction('Accept Failed', () =>
      api.post('/quests/accept', { quest_id: questId }),
    );

  const complete = (questId) =>
    runAction('Complete Failed', () =>
      api.post('/quests/complete', { quest_id: questId }),
    );

  const isQuestActive = (questId) => active.some((q) => q.quest_id === questId);
  const isQuestCompleted = (questId) => completed.includes(questId);

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#ff6b35" />
      </View>
    );
  }

  const renderObjective = (objective, progressItem) => {
    const current = progressItem ? progressItem.current || 0 : 0;
    const required = progressItem ? progressItem.required : objective.count;
    const done = current >= required;
    return (
      <View key={objective.type + objective.target} style={styles.objectiveRow}>
        <Text style={[styles.objectiveText, done && styles.objectiveDone]}>
          {done ? '✓ ' : '☐ '}
          {objective.type}: {objective.target}
        </Text>
        <Text style={[styles.objectiveCount, done && styles.objectiveDone]}>
          {current}/{required}
        </Text>
      </View>
    );
  };

  const renderRewards = (quest) => {
    const rewards = quest.rewards || {};
    const parts = [];
    if (rewards.xp) parts.push(`${rewards.xp} XP`);
    if (rewards.currency) {
      for (const [cur, amt] of Object.entries(rewards.currency)) {
        if (amt) parts.push(`${amt} ${cur}`);
      }
    }
    if (rewards.items) {
      for (const item of rewards.items) {
        parts.push(`${item.quantity}x ${item.name || item.id}`);
      }
    }
    return parts.length ? parts.join(' · ') : 'No rewards';
  };

  const renderCard = (quest, extra) => {
    const questId = quest.quest_id !== undefined ? quest.quest_id : quest.id;
    const name = quest.name;
    const description = quest.description;
    const progressItem = active.find((q) => q.quest_id === questId)?.progress;

    return (
      <View key={questId} style={styles.card}>
        <View style={styles.cardHeader}>
          <Text style={styles.questName}>{name}</Text>
          <Text style={styles.questDifficulty}>{quest.difficulty || 'easy'}</Text>
        </View>
        {description ? <Text style={styles.questDesc}>{description}</Text> : null}

        <View style={styles.objectives}>
          {(quest.objectives || []).map((obj) => renderObjective(obj, progressItem))}
        </View>

        <Text style={styles.rewardsLabel}>Rewards: {renderRewards(quest)}</Text>

        {extra ? (
          <View style={styles.actionArea}>{extra}</View>
        ) : null}
      </View>
    );
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Quests</Text>

      <View style={styles.tabRow}>
        {TABS.map((t) => (
          <TouchableOpacity
            key={t}
            style={[styles.tab, tab === t && styles.tabActive]}
            onPress={() => setTab(t)}
          >
            <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>{t}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {tab === 'Available' && (
        <View>
          {available.length === 0 ? (
            <View style={styles.card}>
              <Text style={styles.emptyText}>No quests available in your region yet.</Text>
            </View>
          ) : (
            available.map((quest) =>
              renderCard(quest, (
                <TouchableOpacity
                  style={styles.button}
                  onPress={() => acceptQuest(quest.id)}
                  disabled={busy}
                >
                  <Text style={styles.buttonText}>
                    {isQuestActive(quest.id) ? 'Active' : isQuestCompleted(quest.id) ? 'Completed' : 'Accept'}
                  </Text>
                </TouchableOpacity>
              )),
            )
          )}
        </View>
      )}

      {tab === 'Active' && (
        <View>
          {active.length === 0 ? (
            <View style={styles.card}>
              <Text style={styles.emptyText}>No active quests. Browse the Available tab.</Text>
            </View>
          ) : (
            active.map((quest) => {
              const allDone = (quest.progress || []).every(
                (p) => (p.current || 0) >= (p.required || 1),
              );
              return renderCard(
                { ...quest, quest_id: quest.quest_id, id: quest.quest_id },
                allDone ? (
                  <TouchableOpacity
                    style={styles.button}
                    onPress={() => complete(quest.quest_id)}
                    disabled={busy}
                  >
                    <Text style={styles.buttonText}>Complete Quest</Text>
                  </TouchableOpacity>
                ) : (
                  <Text style={styles.pendingText}>Objectives not yet met.</Text>
                ),
              );
            })
          )}
        </View>
      )}

      {tab === 'Completed' && (
        <View>
          {completed.length === 0 ? (
            <View style={styles.card}>
              <Text style={styles.emptyText}>No completed quests yet.</Text>
            </View>
          ) : (
            completed.map((questId) => {
              const quest = available.find((q) => q.id === questId) || {
                id: questId,
                name: questId,
              };
              return renderCard(quest);
            })
          )}
        </View>
      )}

      <TouchableOpacity style={styles.refreshButton} onPress={loadQuests}>
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
  tabRow: {
    flexDirection: 'row',
    backgroundColor: '#15182f',
    borderRadius: 12,
    padding: 4,
    marginBottom: 16,
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    alignItems: 'center',
  },
  tabActive: {
    backgroundColor: '#ff6b35',
  },
  tabText: {
    color: '#bbb',
    fontSize: 14,
    fontWeight: '600',
  },
  tabTextActive: {
    color: '#fff',
    fontWeight: '700',
  },
  card: {
    backgroundColor: '#15182f',
    padding: 16,
    borderRadius: 16,
    marginBottom: 16,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  questName: {
    color: '#fff',
    fontSize: 17,
    fontWeight: '700',
    flex: 1,
    marginRight: 8,
  },
  questDifficulty: {
    color: '#888',
    fontSize: 12,
    textTransform: 'capitalize',
  },
  questDesc: {
    color: '#bbb',
    fontSize: 14,
    marginBottom: 12,
    lineHeight: 20,
  },
  objectives: {
    marginBottom: 12,
  },
  objectiveRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 4,
  },
  objectiveText: {
    color: '#ccc',
    fontSize: 14,
    flex: 1,
    marginRight: 8,
  },
  objectiveCount: {
    color: '#aaa',
    fontSize: 13,
  },
  objectiveDone: {
    color: '#4caf50',
  },
  rewardsLabel: {
    color: '#ff6b35',
    fontSize: 13,
    marginBottom: 12,
  },
  pendingText: {
    color: '#888',
    fontSize: 13,
  },
  emptyText: {
    color: '#888',
    fontSize: 14,
  },
  actionArea: {
    marginTop: 4,
  },
  button: {
    backgroundColor: '#ff6b35',
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontWeight: '700',
  },
  refreshButton: {
    marginTop: 8,
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
