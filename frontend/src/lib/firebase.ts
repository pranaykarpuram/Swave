import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyDuuMptjSohD7x9gTG5XB9B31I_o4tVrTw",
  authDomain: "swave-d8549.firebaseapp.com",
  projectId: "swave-d8549",
  storageBucket: "swave-d8549.firebasestorage.app",
  messagingSenderId: "873979695049",
  appId: "1:873979695049:web:928e2c47461153fe266218",
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Authentication and get a reference to the service
export const auth = getAuth(app);

// Initialize Cloud Firestore and get a reference to the service
export const db = getFirestore(app);

export default app;

