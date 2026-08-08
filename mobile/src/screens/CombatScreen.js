import React, { useEffect, useState, useRef } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator,
  Alert, Animated, Easing, Image,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import api from '../services/api';
import { monsterSprite, playSfx } from '../services/assets';
import { setPlayer } from '../store/playerSlice';
import AsyncStorage from '@react-native-async-storage/async-storage';

/**
 * ONE-THUMB PVE COMBAT SCREEN
 *
 * Hooks into the real backend /combat/attack-monster/{id} endpoint.
 * Big attack button sits in the bottom-right thumb zone; everything else
 * is read-only HUD above it. Designed for portrait one-hand play.
 */

const MONSTER_DATA = [
  { id: 1, name: 'Venomtail Rat', level: 1, hp: 30, region: 'Murkfen Hamlet' },
  { id: 2, name: 'Shambling Husk', level: 2, hp: 50, region: 'Shadowfen Bog' },
  { id: 4, name: 'Wraithvine Strangler', level: 4, hp: 65, region: 'Sylvaren Forest' },
  { id: 3, name: 'Kobold Cavern-Scurry', level: 3, hp: 45, region: 'Ironwick' },
  { id: 6, name: 'Cragborn Troll', level: 6, hp: 200, region: 'Zorathar Depths' },
  { id: 8, name: 'Emberfang Salamander', level: 8, hp: 120, region: 'Emberfield' },
  { id: 11, name: 'Shadowclaw Prowler', level: 11, hp: 180, region: 'Frostmead' },
  { id: 13, name: 'Spectral Hound', level: 13, hp: 220, region: 'Wraithmoor Crypts' },
  { id: 14, name: 'Gloomshade Arachnid', level: 14, hp: 250, region: 'Shadowfen Bog' },
  { id: 15, name: 'Grubstake Bandit Chief', level: 15, hp: 400, region: 'Emberfield' },
];

function HpBar({ current, max, color }) {
  const pct = max > 0 ? Math.max(0, Math.min(1, current / max)) : 0;
  return (
    <View style={styles.hpBarTrack}>
      <View style={[styles.hpBarFill, { width: `${pct * 100}%`, backgroundColor: color }]} />
    </View>
  );
}

function CombatScreen({ route }) {
  const dispatch = useDispatch();
  const player = useSelector((state) => state.player);
  const initialMonsterId = route?.params?.monsterId ?? 1;

  const [monster, setMonster] = useState(() =>
    MONSTER_DATA.find((m) => m.id === initialMonsterId) || MONSTER_DATA[0]);
  const [monsterHp, setMonsterHp] = useState(null);
  const [monsterMaxHp, setMonsterMaxHp] = useState(null);
  const [playerHp, setPlayerHp] = useState(null);
  const [playerMana, setPlayerMana] = useState(null);
  const [playerStam, setPlayerStam] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [attacking, setAttacking] = useState(false);
  const [log, setLog] = useState([]);
  const [autoAttack, setAutoAttack] = useState(false);

  const bounce = useRef(new Animated.Value(0)).current;
  const autoTimer = useRef(null);

  const addLog = (entry) => setLog((l) => [entry, ...l].slice(0, 6));

  const loadProfile = async (silent = false) => {
    try {
      if (!silent) setLoadingProfile(true);
      const response = await api.get('/player/profile');
      const d = response.data;
      dispatch(setPlayer({
        id: d.id, username: d.username, level: d.level, experience: d.experience,
        max_hp: d.max_hp, current_hp: d.current_hp, max_mana: d.max_mana,
        current_mana: d.current_mana, max_stamina: d.max_stamina,
        current_stamina: d.current_stamina, currency: d.currency,
      }));
      setPlayerHp(d.current_hp);
      setPlayerMana(d.current_mana);
      setPlayerStam(d.current_stamina);
    } catch (e) {
      if (!silent) Alert.alert('Error', 'Failed to load profile.');
    } finally {
      if (!silent) setLoadingProfile(false);
    }
  };

  const pickMonster = (id) => {
    const m = MONSTER_DATA.find((x) => x.id === id) || MONSTER_DATA[0];
    setMonster(m);
    setMonsterHp(m.hp);
    setMonsterMaxHp(m.hp);
    setLog([`Encountered ${m.name} (Lv ${m.level}).`]);
  };

  const attack = async () => {
    if (attacking) return;
    playSfx(); // tap/attack sound
    setAttacking(true);
    bounce.setValue(0);
    Animated.timing(bounce, { toValue: 1, duration: 160, easing: Easing.out(Easing.quad), useNativeDriver: true }).start();
    try {
      const res = await api.post(`/combat/attack-monster/${monster.id}?skill_id=power_strike`, {});
      const r = res.data;
      setMonsterHp(r.monster_hp);
      setMonsterMaxHp(r.monster_max_hp);
      setPlayerHp(r.player_hp);

      if (r.critical) {
        addLog(`CRITICAL! You deal ${r.damage_dealt} damage.`);
      } else {
        addLog(`You deal ${r.damage_dealt} damage.`);
      }
      if (r.damage_received) addLog(`You take ${r.damage_received} damage.`);

      if (r.monster_defeated) {
        addLog(`▶ ${monster.name} defeated! +${r.experience_gained} XP`);
        if (r.leveled_up) addLog(`🎉 Level up! You are now level ${r.new_level}.`);
        if (r.loot && r.loot.length) {
          const names = r.loot
            .map((l) => `${l.name || l.id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}` +
              (l.quantity > 1 ? ` x${l.quantity}` : ''))
            .join(', ');
          addLog(`Loot: ${names}`);
        }
        // Spawn a new encounter of the same species family
        setTimeout(() => pickMonster(monster.id), 900);
        await loadProfile(true);
      } else if (r.player_hp <= 0) {
        addLog('You were defeated... respawning.');
        await loadProfile(true);
      }
    } catch (e) {
      const detail = e.response?.data?.detail || e.message || 'Attack failed.';
      if (typeof detail === 'string' && detail.includes('respawn')) {
        addLog(`⏳ ${monster.name} is defeated — waiting to respawn.`);
      } else {
        addLog(detail);
      }
    } finally {
      setAttacking(false);
    }
  };

  useEffect(() => {
    loadProfile();
    pickMonster(initialMonsterId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialMonsterId]);

  useEffect(() => {
    if (autoAttack) {
      autoTimer.current = setInterval(attack, 700);
      return () => clearInterval(autoTimer.current);
    }
  }, [autoAttack, attacking, monster]);

  if (loadingProfile) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#ff6b35" />
      </View>
    );
  }

  const scale = bounce.interpolate({ inputRange: [0, 0.5, 1], outputRange: [1, 0.92, 1] });

  return (
    <View style={styles.container}>
      {/* Top HUD */}
      <View style={styles.hud}>
        <View style={styles.statRow}>
          <Text style={styles.statLabel}>Player</Text>
          <Text style={styles.statValue}>Lv {player.level}</Text>
        </View>
        <View style={styles.barWithLabel}>
          <Text style={styles.barLabel}>HP</Text>
          <HpBar current={playerHp ?? player.current_hp} max={player.max_hp} color="#e74c3c" />
          <Text style={styles.barNum}>{playerHp ?? player.current_hp}/{player.max_hp}</Text>
        </View>
        <View style={styles.barWithLabel}>
          <Text style={styles.barLabel}>MP</Text>
          <HpBar current={playerMana ?? player.current_mana} max={player.max_mana} color="#3498db" />
        </View>
        <View style={styles.barWithLabel}>
          <Text style={styles.barLabel}>ST</Text>
          <HpBar current={playerStam ?? player.current_stamina} max={player.max_stamina} color="#f39c12" />
        </View>
      </View>

      {/* Monster */}
      <View style={styles.monsterCard}>
        <View style={styles.monsterSpriteWrap}>
          <Image
            source={{ uri: monsterSprite(monster.id) }}
            style={styles.monsterSprite}
            resizeMode="contain"
          />
        </View>
        <Text style={styles.monsterName}>{monster.name} · Lv {monster.level}</Text>
        <Text style={styles.monsterRegion}>{monster.region}</Text>
        <HpBar current={monsterHp ?? monster.hp} max={monsterMaxHp ?? monster.hp} color="#e67e22" />
        <Text style={styles.barNum}>{monsterHp ?? monster.hp}/{monsterMaxHp ?? monster.hp}</Text>
      </View>

      {/* Battle log */}
      <ScrollView style={styles.log} contentContainerStyle={{ flexGrow: 1, justifyContent: 'flex-end' }}>
        {log.map((entry, i) => (
          <Text key={i} style={[styles.logLine, i === 0 && styles.logLineNew]}>{entry}</Text>
        ))}
      </ScrollView>

      {/* Single-thumb controls */}
      <View style={styles.controls}>
        <View style={styles.monsterPicker}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ alignItems: 'center' }}>
            {MONSTER_DATA.map((m) => (
              <TouchableOpacity
                key={m.id}
                onPress={() => { playSfx(); pickMonster(m.id); }}
                style={[styles.pickChip, m.id === monster.id && styles.pickChipActive]}
              >
                <Text style={styles.pickChipText}>{m.name.split(' ')[0]}</Text>
                <Text style={styles.pickChipLv}>Lv{m.level}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        <View style={styles.actionRow}>
          <TouchableOpacity
            style={[styles.autoBtn, autoAttack && styles.autoBtnOn]}
            onPress={() => { playSfx(); setAutoAttack((v) => !v); }}
          >
            <Text style={styles.autoBtnText}>{autoAttack ? '⏸' : '▶'}</Text>
          </TouchableOpacity>
          <Animated.View style={{ transform: [{ scale }] }}>
            <TouchableOpacity
              style={[styles.attackBtn, attacking && styles.attackBtnDown]}
              onPress={attack}
              activeOpacity={0.7}
            >
              <Text style={styles.attackBtnText}>ATTACK</Text>
            </TouchableOpacity>
          </Animated.View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f0f1a', padding: 14 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0f0f1a' },

  hud: { backgroundColor: '#15182f', borderRadius: 16, padding: 14, marginBottom: 12 },
  statRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  statLabel: { color: '#ff6b35', fontWeight: '700', fontSize: 16 },
  statValue: { color: '#fff', fontWeight: '700' },
  barWithLabel: { flexDirection: 'row', alignItems: 'center', marginVertical: 2 },
  barLabel: { color: '#888', width: 28, fontSize: 12 },
  barNum: { color: '#ccc', marginLeft: 8, fontSize: 12 },
  hpBarTrack: { flex: 1, height: 10, backgroundColor: '#2a2a3e', borderRadius: 5, overflow: 'hidden' },
  hpBarFill: { height: '100%', borderRadius: 5 },

  monsterCard: {
    backgroundColor: '#1a1a2e', borderRadius: 16, padding: 14, marginBottom: 12,
    borderWidth: 1, borderColor: '#2a2a3e', alignItems: 'center',
  },
  monsterSpriteWrap: {
    width: 88, height: 88, borderRadius: 12, marginBottom: 8,
    backgroundColor: '#0f0f1a', borderWidth: 1, borderColor: '#2a2a3e',
    alignItems: 'center', justifyContent: 'center',
  },
  monsterSprite: {
    width: 64, height: 64,
  },
  monsterName: { color: '#fff', fontSize: 20, fontWeight: '700' },
  monsterRegion: { color: '#888', fontSize: 12, marginBottom: 8 },
  monsterRow: { flexDirection: 'row', alignItems: 'center' },

  log: { flex: 1, backgroundColor: '#11111f', borderRadius: 12, padding: 10, marginBottom: 12 },
  logLine: { color: '#aaa', fontSize: 13, marginVertical: 1 },
  logLineNew: { color: '#fff', fontWeight: '600' },

  controls: { },
  monsterPicker: { marginBottom: 10 },
  pickChip: {
    backgroundColor: '#15182f', borderRadius: 20, paddingHorizontal: 14, paddingVertical: 8,
    marginRight: 8, flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#2a2a3e',
  },
  pickChipActive: { borderColor: '#ff6b35', backgroundColor: '#24314a' },
  pickChipText: { color: '#fff', fontSize: 13, fontWeight: '600' },
  pickChipLv: { color: '#ff6b35', fontSize: 11, marginLeft: 6 },

  actionRow: { flexDirection: 'row', alignItems: 'center' },
  autoBtn: {
    width: 56, height: 56, borderRadius: 28, backgroundColor: '#15182f',
    alignItems: 'center', justifyContent: 'center', marginRight: 12,
    borderWidth: 1, borderColor: '#2a2a3e',
  },
  autoBtnOn: { borderColor: '#27ae60' },
  autoBtnText: { color: '#fff', fontSize: 22 },
  attackBtn: {
    flex: 1, height: 66, borderRadius: 22, backgroundColor: '#ff6b35',
    alignItems: 'center', justifyContent: 'center', shadowColor: '#000', shadowOpacity: 0.4, shadowRadius: 8, elevation: 6,
  },
  attackBtnDown: { backgroundColor: '#e55a2b' },
  attackBtnText: { color: '#fff', fontSize: 22, fontWeight: '800', letterSpacing: 2 },
});

export default CombatScreen;
