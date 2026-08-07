import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  TextInput,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
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

export default function ShopScreen() {
  const dispatch = useDispatch();
  const player = useSelector((state) => state.player);
  const [loading, setLoading] = useState(true);
  const [merchants, setMerchants] = useState([]);
  const [selectedMerchant, setSelectedMerchant] = useState(null);
  const [shopData, setShopData] = useState(null);
  const [currency, setCurrency] = useState({ kupdun: 0, zirdun: 0, guldun: 0 });
  const [inventory, setInventory] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [buyQuantity, setBuyQuantity] = useState('1');
  const [sellQuantity, setSellQuantity] = useState('1');
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState('buy');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [merchantRes, profileRes, invRes] = await Promise.all([
        api.get('/shop/'),
        api.get('/player/profile'),
        api.get('/inventory/'),
      ]);
      setMerchants(merchantRes.data || []);
      const cur = profileRes.data.currency || { kupdun: 0, zirdun: 0, guldun: 0 };
      setCurrency(cur);
      setInventory(invRes.data.item_box || []);
    } catch (error) {
      Alert.alert('Error', 'Failed to load merchants.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openShop = async (merchantId) => {
    try {
      setBusy(true);
      const response = await api.get(`/shop/${merchantId}`);
      setShopData(response.data);
      setSelectedMerchant(merchantId);
      setSelectedItem(null);
      setBuyQuantity('1');
    } catch (error) {
      Alert.alert('Error', 'Failed to load merchant inventory.');
    } finally {
      setBusy(false);
    }
  };

  const buyItem = async () => {
    if (!selectedItem || busy) return;
    const qty = parseInt(buyQuantity, 10) || 1;
    if (qty < 1) return;
    setBusy(true);
    try {
      const response = await api.post(
        `/shop/buy/${selectedMerchant}/${selectedItem.id}?quantity=${qty}`,
      );
      dispatch(updateCurrency({
        [response.data.currency || 'kupdun']:
          (currency[response.data.currency || 'kupdun'] || 0) -
          (response.data.cost || 0),
      }));
      const [shopRes, profileRes, invRes] = await Promise.all([
        api.get(`/shop/${selectedMerchant}`),
        api.get('/player/profile'),
        api.get('/inventory/'),
      ]);
      setShopData(shopRes.data);
      setCurrency(profileRes.data.currency || { kupdun: 0, zirdun: 0, guldun: 0 });
      setInventory(invRes.data.item_box || []);
      setSelectedItem(null);
      setBuyQuantity('1');
      Alert.alert('Purchased', response.data.message);
    } catch (error) {
      const detail = error.response?.data?.detail || error.message;
      Alert.alert('Buy Failed', typeof detail === 'string' ? detail : 'Request failed.');
    } finally {
      setBusy(false);
    }
  };

  const sellItems = async () => {
    if (!selectedItem || busy) return;
    const qty = parseInt(sellQuantity, 10) || 1;
    if (qty < 1) return;
    setBusy(true);
    try {
      const response = await api.post(
        `/shop/sell/${selectedItem.id}?quantity=${qty}`,
      );
      const [profileRes, invRes] = await Promise.all([
        api.get('/player/profile'),
        api.get('/inventory/'),
      ]);
      setCurrency(profileRes.data.currency || { kupdun: 0, zirdun: 0, guldun: 0 });
      setInventory(invRes.data.item_box || []);
      setSelectedItem(null);
      setSellQuantity('1');
      Alert.alert('Sold', response.data.message);
    } catch (error) {
      const detail = error.response?.data?.detail || error.message;
      Alert.alert('Sell Failed', typeof detail === 'string' ? detail : 'Request failed.');
    } finally {
      setBusy(false);
    }
  };

  const formatCurrency = (amount, type) => {
    if (type === 'kupdun') return `${amount} K`;
    if (type === 'zirdun') return `${amount} Z`;
    if (type === 'guldun') return `${amount} G`;
    return `${amount} ${type}`;
  };

  const getCurrencyBalance = (type) => {
    return currency[type] || 0;
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
          <Text style={styles.title}>Shop</Text>
          <View style={styles.currencyRow}>
            <Text style={styles.currency}>K {currency.kupdun}</Text>
            <Text style={styles.currency}>Z {currency.zirdun}</Text>
            <Text style={styles.currency}>G {currency.guldun}</Text>
          </View>
        </View>

        {!selectedMerchant && (
          <View>
            <Text style={styles.sectionTitle}>Merchants</Text>
            {merchants.map((merchant) => (
              <TouchableOpacity
                key={merchant.id}
                style={styles.card}
                onPress={() => openShop(merchant.id)}
              >
                <Text style={styles.merchantName}>{merchant.name}</Text>
                <Text style={styles.merchantRegion}>{merchant.region}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {selectedMerchant && shopData && (
          <View>
            <TouchableOpacity
              style={styles.backButton}
              onPress={() => {
                setSelectedMerchant(null);
                setShopData(null);
                setSelectedItem(null);
              }}
            >
              <Text style={styles.backText}>← Back to Merchants</Text>
            </TouchableOpacity>

            <View style={styles.card}>
              <Text style={styles.merchantName}>{shopData.name}</Text>
              <Text style={styles.merchantRegion}>{shopData.region}</Text>
            </View>

            <View style={styles.tabRow}>
              <TouchableOpacity
                style={[styles.tab, tab === 'buy' && styles.tabActive]}
                onPress={() => {
                  setTab('buy');
                  setSelectedItem(null);
                }}
              >
                <Text style={[styles.tabText, tab === 'buy' && styles.tabTextActive]}>
                  Buy
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.tab, tab === 'sell' && styles.tabActive]}
                onPress={() => {
                  setTab('sell');
                  setSelectedItem(null);
                }}
              >
                <Text style={[styles.tabText, tab === 'sell' && styles.tabTextActive]}>
                  Sell
                </Text>
              </TouchableOpacity>
            </View>

            {tab === 'buy' && (
              <View style={styles.card}>
                <Text style={styles.cardTitle}>Merchant Inventory</Text>
                {(shopData.items || []).length === 0 ? (
                  <Text style={styles.emptyText}>This merchant has no items for sale.</Text>
                ) : (
                  (shopData.items || []).map((item) => {
                    const color = RARITY_COLORS[item.rarity] || '#ffffff';
                    return (
                      <TouchableOpacity
                        key={item.id}
                        style={[
                          styles.itemRow,
                          selectedItem?.id === item.id && styles.itemRowSelected,
                        ]}
                        onPress={() => {
                          setSelectedItem(item);
                          setBuyQuantity('1');
                        }}
                      >
                        <View style={styles.itemInfo}>
                          <Text style={[styles.itemName, { color }]}>{item.name}</Text>
                          <Text style={styles.itemPrice}>
                            {formatCurrency(item.price, item.currency)} each · Stock: {item.quantity}
                          </Text>
                        </View>
                        <Text style={styles.itemStock}>{item.quantity}x</Text>
                      </TouchableOpacity>
                    );
                  })
                )}
              </View>
            )}

            {tab === 'sell' && (
              <View style={styles.card}>
                <Text style={styles.cardTitle}>Your Inventory</Text>
                {inventory.length === 0 ? (
                  <Text style={styles.emptyText}>Your item box is empty.</Text>
                ) : (
                  inventory.map((item) => {
                    const sellPrice = Math.max(1, (item.value || 1) / 2);
                    const currencyType = item.value_currency || 'kupdun';
                    return (
                      <TouchableOpacity
                        key={item.id}
                        style={[
                          styles.itemRow,
                          selectedItem?.id === item.id && styles.itemRowSelected,
                        ]}
                        onPress={() => {
                          setSelectedItem(item);
                          setSellQuantity('1');
                        }}
                      >
                        <View style={styles.itemInfo}>
                          <Text style={styles.itemName}>{item.name}</Text>
                          <Text style={styles.itemPrice}>
                            Sells for {sellPrice} {currencyType} each · Qty: {item.quantity}
                          </Text>
                        </View>
                        <Text style={styles.itemStock}>{item.quantity}x</Text>
                      </TouchableOpacity>
                    );
                  })
                )}
              </View>
            )}

            {selectedItem && (
              <View style={styles.actionCard}>
                <Text style={styles.actionTitle}>{selectedItem.name}</Text>
                {tab === 'buy' ? (
                  <>
                    <Text style={styles.actionDetail}>
                      Price: {formatCurrency(selectedItem.price, selectedItem.currency)} each
                    </Text>
                    <Text style={styles.actionDetail}>
                      Your balance:{' '}
                      {formatCurrency(
                        getCurrencyBalance(selectedItem.currency),
                        selectedItem.currency,
                      )}
                    </Text>
                    <View style={styles.qtyRow}>
                      <Text style={styles.qtyLabel}>Quantity:</Text>
                      <TextInput
                        style={styles.qtyInput}
                        keyboardType="numeric"
                        value={buyQuantity}
                        onChangeText={setBuyQuantity}
                      />
                    </View>
                    <TouchableOpacity
                      style={[
                        styles.button,
                        getCurrencyBalance(selectedItem.currency) <
                          selectedItem.price * (parseInt(buyQuantity, 10) || 1) &&
                          styles.buttonDisabled,
                      ]}
                      onPress={buyItem}
                      disabled={
                        busy ||
                        getCurrencyBalance(selectedItem.currency) <
                          selectedItem.price * (parseInt(buyQuantity, 10) || 1)
                      }
                    >
                      <Text style={styles.buttonText}>
                        Buy {parseInt(buyQuantity, 10) || 1}x (
                        {formatCurrency(
                          selectedItem.price * (parseInt(buyQuantity, 10) || 1),
                          selectedItem.currency,
                        )}
                        )
                      </Text>
                    </TouchableOpacity>
                  </>
                ) : (
                  <>
                    <Text style={styles.actionDetail}>
                      Sell price: {Math.max(1, (selectedItem.value || 1) / 2)}{' '}
                      {selectedItem.value_currency || 'kupdun'} each
                    </Text>
                    <View style={styles.qtyRow}>
                      <Text style={styles.qtyLabel}>Quantity:</Text>
                      <TextInput
                        style={styles.qtyInput}
                        keyboardType="numeric"
                        value={sellQuantity}
                        onChangeText={setSellQuantity}
                      />
                    </View>
                    <TouchableOpacity
                      style={styles.button}
                      onPress={sellItems}
                      disabled={
                        busy ||
                        (parseInt(sellQuantity, 10) || 1) < 1 ||
                        (parseInt(sellQuantity, 10) || 1) > (selectedItem.quantity || 0)
                      }
                    >
                      <Text style={styles.buttonText}>
                        Sell {parseInt(sellQuantity, 10) || 1}x
                      </Text>
                    </TouchableOpacity>
                  </>
                )}
              </View>
            )}
          </View>
        )}

        <TouchableOpacity
          style={styles.refreshButton}
          onPress={async () => {
            await loadData();
            if (selectedMerchant) {
              try {
                const shopRes = await api.get(`/shop/${selectedMerchant}`);
                setShopData(shopRes.data);
              } catch {}
            }
          }}
        >
          <Text style={styles.refreshText}>Refresh</Text>
        </TouchableOpacity>
      </ScrollView>
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
  sectionTitle: {
    color: '#ff6b35',
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 12,
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
  merchantName: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 4,
  },
  merchantRegion: {
    color: '#aaa',
    fontSize: 14,
  },
  backButton: {
    marginBottom: 12,
    paddingVertical: 8,
  },
  backText: {
    color: '#ff6b35',
    fontSize: 15,
    fontWeight: '600',
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
  itemRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomColor: '#252b47',
    borderBottomWidth: 1,
    paddingHorizontal: 8,
    marginHorizontal: -8,
    borderRadius: 8,
  },
  itemRowSelected: {
    backgroundColor: '#1f1f3b',
  },
  itemInfo: {
    flex: 1,
    marginRight: 8,
  },
  itemName: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
  },
  itemPrice: {
    color: '#aaa',
    fontSize: 13,
    marginTop: 2,
  },
  itemStock: {
    color: '#888',
    fontSize: 14,
  },
  emptyText: {
    color: '#888',
    fontSize: 14,
    paddingVertical: 8,
  },
  actionCard: {
    backgroundColor: '#15182f',
    padding: 16,
    borderRadius: 16,
    marginBottom: 16,
  },
  actionTitle: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 8,
  },
  actionDetail: {
    color: '#bbb',
    fontSize: 14,
    marginBottom: 4,
  },
  qtyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    marginBottom: 12,
  },
  qtyLabel: {
    color: '#ccc',
    fontSize: 14,
    marginRight: 8,
  },
  qtyInput: {
    width: 70,
    height: 40,
    backgroundColor: '#1f1f3b',
    borderRadius: 10,
    paddingHorizontal: 12,
    color: '#fff',
    textAlign: 'center',
  },
  button: {
    backgroundColor: '#ff6b35',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: {
    opacity: 0.4,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 15,
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
