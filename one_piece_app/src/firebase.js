import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
// import { getAnalytics } from "firebase/analytics";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyD9Hr934rYuLXmfkYLFUDmc_iD8OOjeqOo",
  authDomain: "one-piece-card-game-index.firebaseapp.com",
  projectId: "one-piece-card-game-index",
  storageBucket: "one-piece-card-game-index.firebasestorage.app",
  messagingSenderId: "434521336426",
  appId: "1:434521336426:web:6677b069faa81e0d60b813",
  measurementId: "G-H3XN5RHTMZ"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firestore (The database where we will store the wishlist)
export const db = getFirestore(app);
