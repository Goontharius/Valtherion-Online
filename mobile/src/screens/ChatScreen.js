import React, { useEffect, useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet } from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import WebSocketService from '../services/websocket';
import { addMessage } from '../store/chatSlice';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function ChatScreen() {
  const dispatch = useDispatch();
  const messages = useSelector((state) => state.chat.messages);
  const [messageText, setMessageText] = useState('');
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const connectWebSocket = async () => {
      const token = await AsyncStorage.getItem('auth_token');
      if (token) {
        WebSocketService.connect(token);
        WebSocketService.on('message', handleIncomingMessage);
        WebSocketService.on('open', () => setConnected(true));
        WebSocketService.on('close', () => setConnected(false));
      }
    };

    connectWebSocket();

    return () => {
      WebSocketService.off('message', handleIncomingMessage);
      WebSocketService.disconnect();
    };
  }, []);

  const handleIncomingMessage = (data) => {
    if (data?.type === 'chat') {
      dispatch(addMessage(data));
    }
  };

  const sendMessage = () => {
    if (!messageText.trim()) return;
    WebSocketService.send({ type: 'chat', channel: 'general', message: messageText });
    setMessageText('');
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Chat</Text>
        <Text style={styles.status}>{connected ? 'Connected' : 'Disconnected'}</Text>
      </View>
      <FlatList
        data={messages}
        keyExtractor={(item, index) => `${item.type}-${index}`}
        renderItem={({ item }) => (
          <View style={styles.messageBubble}>
            <Text style={styles.sender}>{item.from || item.sender_name || 'System'}</Text>
            <Text style={styles.message}>{item.message}</Text>
          </View>
        )}
        contentContainerStyle={styles.messageList}
      />
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          placeholder="Type a message"
          placeholderTextColor="#888"
          value={messageText}
          onChangeText={setMessageText}
        />
        <TouchableOpacity style={styles.sendButton} onPress={sendMessage}>
          <Text style={styles.sendText}>Send</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f1a',
    padding: 16,
  },
  header: {
    marginBottom: 16,
  },
  title: {
    color: '#ff6b35',
    fontSize: 24,
    fontWeight: '700',
  },
  status: {
    color: '#ccc',
    marginTop: 4,
  },
  messageList: {
    paddingBottom: 16,
  },
  messageBubble: {
    marginBottom: 12,
    backgroundColor: '#15182f',
    borderRadius: 14,
    padding: 12,
  },
  sender: {
    color: '#ff6b35',
    marginBottom: 4,
  },
  message: {
    color: '#fff',
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    borderTopColor: '#252b47',
    borderTopWidth: 1,
    paddingTop: 12,
  },
  input: {
    flex: 1,
    height: 46,
    backgroundColor: '#1f1f3b',
    borderRadius: 12,
    paddingHorizontal: 12,
    color: '#fff',
    marginRight: 8,
  },
  sendButton: {
    backgroundColor: '#ff6b35',
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  sendText: {
    color: '#fff',
    fontWeight: '700',
  },
});
