#!/usr/bin/env python3
"""
Script para treinar a wake word.
Executar: python train_wake_word.py
"""
import sys
import os

# Ajusta o path para que os imports funcionem corretamente
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from core.wake_word_service import wake_word

def main():
    print("\n" + "="*60)
    print("🎤 TREINAMENTO DA WAKE WORD - OMNISCIENT")
    print("="*60)
    
    status = wake_word.get_status()
    
    if status['trained']:
        print(f"\n✅ Wake word já treinada com {status['num_templates']} amostras.")
        print(f"   Threshold atual: {status['threshold']}")
        
        choice = input("\nDeseja treinar novamente? (s/n): ").strip().lower()
        if choice != 's':
            print("Cancelado.")
            return
        
        wake_word.clear_templates()
    
    print("\nVou gravar sua voz dizendo a wake word.")
    print("Por favor, fale 'OMINI' de forma clara e natural.\n")
    
    # Opções
    print("Opções:")
    print("  1. Treino rápido (3 amostras)")
    print("  2. Treino normal (5 amostras)")
    print("  3. Treino completo (8 amostras)")
    print("  4. Sair")
    
    choice = input("\nEscolha (1-4): ").strip()
    
    num_samples = {
        '1': 3,
        '2': 5,
        '3': 8
    }.get(choice, 5)
    
    if choice == '4':
        print("Saindo...")
        return
    
    success = wake_word.train(num_samples=num_samples, duration_each=2.0)
    
    if success:
        print("\n" + "="*60)
        print("🎉 PARABÉNS! Wake word treinada com sucesso!")
        print("="*60)
        print("\nAgora o agente deve reconhecer sua voz quando você")
        print("dizer 'OMINI' no início da frase.")
        print("\nDica: Se não reconhecer bem, execute novamente")
        print("para ajustar com mais amostras.")
        print("="*60)
    else:
        print("\n❌ Treinamento falhou. Tente novamente.")

if __name__ == "__main__":
    main()
