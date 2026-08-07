class WebSocketService {
  constructor() {
    this.ws = null;
    this.listeners = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.token = null;
  }

  connect(token) {
    if (!token) {
      console.warn('WebSocket connect attempted without token');
      return;
    }

    this.token = token;
    const WS_BASE = __DEV__
      ? 'ws://localhost:8000'
      : 'wss://api.valtheriononline.com';
    const wsUrl = `${WS_BASE}/ws/${token}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.trigger('open');
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.trigger('message', data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.trigger('close');
      this.reconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.trigger('error', error);
    };
  }

  reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnect attempts reached');
      return;
    }

    if (!this.token) {
      console.warn('No token available for websocket reconnect');
      return;
    }

    setTimeout(() => {
      this.reconnectAttempts += 1;
      console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
      this.connect(this.token);
    }, 5000 * Math.min(this.reconnectAttempts + 1, 5));
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket not connected');
    }
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter((cb) => cb !== callback);
    }
  }

  trigger(event, ...args) {
    if (this.listeners[event]) {
      this.listeners[event].forEach((callback) => callback(...args));
    }
  }
}

export default new WebSocketService();
