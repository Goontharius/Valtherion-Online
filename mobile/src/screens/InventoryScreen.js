import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Modal,
} from 'react-native';
import { useDispatch } from 'react-redux';
import api from '../services/api';
import { updateCurrency } from '../store/playerSlice';

const RARITY_COLORS = {
  Common: '#ffffff',
  Uncommon: '#00ff00',
  Rare: '#0088ff',
  Epic: '#aa00ff',
  Legendary: '#ff8800',
  'God-Tier': '#ff0000',
};

const EQUIPMENT_SLOTS = [
  ['weapon', 'Weapon'],
  ['shield', 'Shield'],
  ['helmet', 'Helmet'],
  ['chest', 'Chest'],
  ['legs', 'Legs'],
  ['boots', 'Boots'],
  ['gloves', 'Gloves'],
  ['ring', 'Ring'],
  ['amulet', 'Amulet'],
  ['trinket', 'Trinket'],
];

export default function InventoryScreen() {
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(true);
  const [itemBox, setItemBox] = useState([]);
  const [hotbar, setHotbar] = useState([]);
  const [equipment, setEquipment] = useState({});
  const [currency, setCurrency] = useState({ kupdun: 0, zirdun: 0, guldun: 0 });
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);

  const loadInventory = async () => {
    try {
      setLoading(true);
      const response = await api.get('/inventory/');
      setItemBox(response.data.item_box || []);
      setHotbar(response.data.hotbar || []);
      setEquipment(response.data.equipment || {});
      const profile = await api.get('/player/profile');
      setCurrency(profile.data.currency || { kupdun: 0, zirdun: 0, guldun: 0 });
    } catch (error) {
      Alert.alert('Error', 'Failed to load inventory.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInventory();
  }, []);

  const runAction = async (label, request) => {
    if (busy) return;
    setBusy(true);
    try {
      await request();
      await loadInventory();
      setSelected(null);
    } catch (error) {
      const detail = error.response?.data?.detail || error.message;
      Alert.alert(label, typeof detail === 'string' ? detail : 'Request failed.');
    } finally {
      setBusy(false);
    }
  };

  const equipItem = (item) =>
    runAction('Equip Failed', () => api.post(`/inventory/equip/${item.id}`));

  const unequipItem = (slot) =>
    runAction('Unequip Failed', () => api.post(`/inventory/unequip/${slot}`));

  const consumeItem = (item) =>
    runAction('Consume Failed', () =>
      api.post('/player/consume', { item_id: item.id, quantity: 1 }),
    );

  const sellItem = (item) =>
    runAction('Sell Failed', () => api.post(`/shop/sell/${item.id}?quantity=1`));

  const assignHotbar = (item) =>
    runAction('Hotbar Failed', async () => {
      const firstFree = [...Array(8).keys()].find(
        (i) => !hotbar.some((h) => h.slot === i + 1),
      );
      const slot = firstFree === undefined ? 8 : firstFree + 1;
      await api.post(`/inventory/hotbar?slot=${slot}&item_id=${item.id}`);
    });

  const clearHotbarSlot = (slot) =>
    runAction('Hotbar Failed', async () => {
      const existing = hotbar.find((h) => h.slot === slot);
      if (existing) {
        await api.post(`/inventory/hotbar?slot=${slot}&item_id=`);
      }
    });

  const selectedItem = selected ? itemBox.find((i) => i.id === selected) : null;
  const selectedRarity = selectedItem ? RARITY_COLORS[selectedItem.rarity] || '#ffffff' : '#fff';

  const renderItemCell = (item) => {
    const color = RARITY_COLORS[item.rarity] || '#ffffff';
    return (
      <TouchableOpacity
        key={item.id}
        style={[styles.itemCell, { borderColor: color }]}
        onPress={() => setSelected(item.id)}
      >
        <Text style={[styles.itemIcon, { color }]}>
          {item.name ? item.name.substring(0, 2).toUpperCase() : '??'}
        </Text>
        <Text style={styles.itemName} numberOfLines={1}>
          {item.name}
        </Text>
        {item.quantity > 1 && <Text style={styles.itemQty}>x{item.quantity}</Text>}
      </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#ff6b35" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.headerRow}>
          <Text style={styles.title}>Inventory</Text>
          <View style={styles.currencyRow}>
            <Text style={styles.currency}>K {currency.kupdun}</Text>
            <Text style={styles.currency}>Z {currency.zirdun}</Text>
            <Text style={styles.currency}>G {currency.guldun}</Text>
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Equipment</Text>
          <View style={styles.equipGrid}>
            {EQUIPMENT_SLOTS.map(([slot, label]) => {
              const item = equipment[slot];
              const color = item ? RARITY_COLORS[item.rarity] || '#ffffff' : '#444';
              return (
                <TouchableOpacity
                  key={slot}
                  style={[styles.equipCell, { borderColor: color }]}
                  onPress={() => (item ? unequipItem(slot) : null)}
                  disabled={!item}
                >
                  <Text style={[styles.equipIcon, { color }]}>
                    {item ? (item.name || '?').substring(0, 1).toUpperCase() : '+'}
                  </Text>
                  <Text style={styles.equipLabel} numberOfLines={1}>
                    {item ? item.name : label}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Item Box ({itemBox.length})</Text>
          {itemBox.length === 0 ? (
            <Text style={styles.emptyText}>Your item box is empty.</Text>
          ) : (
            <View style={styles.itemGrid}>{itemBox.map(renderItemCell)}</View>
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Hotbar</Text>
          <View style={styles.hotbarRow}>
            {[...Array(8).keys()].map((i) => {
              const slot = i + 1;
              const entry = hotbar.find((h) => h.slot === slot);
              const item = entry
                ? itemBox.find((inv) => inv.id === entry.item_id)
                : null;
              const color = item ? RARITY_COLORS[item.rarity] || '#ffffff' : '#444';
              return (
                <TouchableOpacity
                  key={slot}
                  style={[styles.hotbarCell, { borderColor: color }]}
                  onPress={() =>
                    entry ? clearHotbarSlot(slot) : selectedItem && assignHotbar(selectedItem)
                  }
                >
                  <Text style={[styles.hotbarNum, { color }]}>{slot}</Text>
                  <Text style={styles.hotbarIcon} numberOfLines={1}>
                    {item ? (item.name || '?').substring(0, 1).toUpperCase() : '·'}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>

        <TouchableOpacity style={styles.refreshButton} onPress={loadInventory}>
          <Text style={styles.refreshText}>Refresh</Text>
        </TouchableOpacity>
      </ScrollView>

      <Modal
        visible={!!selectedItem}
        transparent
        animationType="fade"
        onRequestClose={() => setSelected(null)}
      >
        <TouchableOpacity
          style={styles.modalBackdrop}
          activeOpacity={1}
          onPress={() => setSelected(null)}
        >
          <View style={styles.modalCard}>
            <Text style={[styles.modalName, { color: selectedRarity }]}>
              {selectedItem?.name}
            </Text>
            {selectedItem?.rarity && (
              <Text style={styles.modalRarity}>{selectedItem.rarity}</Text>
            )}
            <Text style={styles.modalMeta}>
              Qty: {selectedItem?.quantity} · Wt: {selectedItem?.weight}
            </Text>
            {selectedItem?.description && (
              <Text style={styles.modalDesc}>{selectedItem.description}</Text>
            )}

            <View style={styles.actionRow}>
              {(selectedItem?.type === 'weapon' ||
                selectedItem?.type === 'armor' ||
                selectedItem?.type === 'accessory' ||
                selectedItem?.type === 'shield') && (
                <TouchableOpacity
                  style={styles.actionButton}
                  onPress={() => equipItem(selectedItem)}
                  disabled={busy}
                >
                  <Text style={styles.actionText}>Equip</Text>
                </TouchableOpacity>
              )}
              {selectedItem?.type === 'consumable' && (
                <TouchableOpacity
                  style={styles.actionButton}
                  onPress={() => consumeItem(selectedItem)}
                  disabled={busy}
                >
                  <Text style={styles.actionText}>Use</Text>
                </TouchableOpacity>
              )}
              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => assignHotbar(selectedItem)}
                disabled={busy}
              >
                <Text style={styles.actionText}>Hotbar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => sellItem(selectedItem)}
                disabled={busy}
              >
                <Text style={styles.actionText}>Sell</Text>
              </TouchableOpacity>
            </View>
          </View>
        </TouchableOpacity>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f1a',
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0f0f1a',
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  title: {
    color: '#ff6b35',
    fontSize: 28,
    fontWeight: '700',
  },
  currencyRow: {
    flexDirection: 'row',
  },
  currency: {
    color: '#ddd',
    fontSize: 14,
    marginLeft: 10,
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
  emptyText: {
    color: '#888',
    fontSize: 14,
  },
  equipGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  equipCell: {
    width: '31%',
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 4,
    marginBottom: 10,
    alignItems: 'center',
    backgroundColor: '#1f1f3b',
  },
  equipIcon: {
    fontSize: 20,
    fontWeight: '700',
  },
  equipLabel: {
    color: '#ccc',
    fontSize: 11,
    marginTop: 4,
  },
  itemGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  itemCell: {
    width: '31%',
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 4,
    marginBottom: 10,
    alignItems: 'center',
    backgroundColor: '#1f1f3b',
  },
  itemIcon: {
    fontSize: 22,
    fontWeight: '700',
  },
  itemName: {
    color: '#ddd',
    fontSize: 11,
    marginTop: 6,
    textAlign: 'center',
  },
  itemQty: {
    color: '#aaa',
    fontSize: 11,
    marginTop: 2,
  },
  hotbarRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  hotbarCell: {
    width: '11.5%',
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: 'center',
    backgroundColor: '#1f1f3b',
  },
  hotbarNum: {
    fontSize: 10,
  },
  hotbarIcon: {
    color: '#ddd',
    fontSize: 18,
    fontWeight: '700',
    marginTop: 2,
  },
  refreshButton: {
    marginTop: 8,
    backgroundColor: '#ff6b35',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  refreshText: {
    color: '#fff',
    fontWeight: '700',
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    padding: 30,
  },
  modalCard: {
    backgroundColor: '#15182f',
    borderRadius: 16,
    padding: 20,
  },
  modalName: {
    fontSize: 22,
    fontWeight: '700',
  },
  modalRarity: {
    color: '#aaa',
    fontSize: 13,
    marginTop: 4,
  },
  modalMeta: {
    color: '#bbb',
    fontSize: 13,
    marginTop: 8,
  },
  modalDesc: {
    color: '#ccc',
    fontSize: 14,
    marginTop: 12,
    lineHeight: 20,
  },
  actionRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginTop: 20,
  },
  actionButton: {
    width: '31%',
    backgroundColor: '#ff6b35',
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
    marginBottom: 8,
  },
  actionText: {
    color: '#fff',
    fontWeight: '700',
  },
});
